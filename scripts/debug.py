#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped, PoseStamped
import cv2
from cv_bridge import CvBridge
import numpy as np
import tf2_ros
import tf2_geometry_msgs

class BlueSquare3DWorldFinder(Node):
    def __init__(self):
        super().__init__('find_blue_square_3d_world')
        self.bridge = CvBridge()

        self.rgb_sub = self.create_subscription(Image, '/color/image_raw', self.rgb_callback, 10)
        self.depth_sub = self.create_subscription(Image, '/aligned_depth_to_color/image_raw', self.depth_callback, 10)
        self.caminfo_sub = self.create_subscription(CameraInfo, '/color/camera_info', self.caminfo_callback, 10)

        self.rgb_image = None
        self.depth_image = None
        self.K = None
        self.image_header = None

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.pose_pub = self.create_publisher(PoseStamped, '/blue_square_pose', 10)
        self.timer = self.create_timer(0.1, self.process)
        
        # DEBUG COUNTERS
        self.detection_count = 0
        self.last_detection_time = None

    def caminfo_callback(self, msg):
        if self.K is None:
            self.K = np.array(msg.k).reshape((3,3))
            self.get_logger().info("Camera intrinsics received.")

    def rgb_callback(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.image_header = msg.header

    def depth_callback(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')

    def process(self):
        if self.rgb_image is None or self.depth_image is None or self.K is None:
            return

        img = self.rgb_image.copy()
        height, width = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # ORIGINAL DETECTION
        lower_blue = np.array([100, 150, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # **DEBUG: Show detection info**
        mask_area = cv2.countNonZero(mask)
        mask_percentage = (mask_area / (width * height)) * 100

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # DEBUG INFO
        self.get_logger().info(f"🔍 DEBUG: Mask area: {mask_area} pixels ({mask_percentage:.1f}% of image)")
        self.get_logger().info(f"🔍 DEBUG: Found {len(contours)} contours")
        
        if contours:
            areas = [cv2.contourArea(c) for c in contours]
            self.get_logger().info(f"🔍 DEBUG: Contour areas: {areas}")

        # FIND BEST CONTOUR
        valid_contours = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 50:  # Minimum area
                # Check if it's roughly square-like
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                self.get_logger().info(f"🔍 DEBUG: Contour {i} - Area: {area}, Vertices: {len(approx)}")
                
                if len(approx) >= 4:  # At least 4 corners
                    valid_contours.append((contour, area))

        if not valid_contours:
            # **DETECTION FAILURE DEBUG**
            now = self.get_clock().now()
            if self.last_detection_time is not None:
                gap = (now - self.last_detection_time).nanoseconds / 1e9
                if gap > 1.0:  # More than 1 second gap
                    self.get_logger().warn(f"❌ NO DETECTION for {gap:.1f}s - Mask: {mask_percentage:.1f}%, Contours: {len(contours)}")
            
            # **SAVE DEBUG IMAGES**
            cv2.imwrite('/tmp/debug_rgb.jpg', img)
            cv2.imwrite('/tmp/debug_mask.jpg', mask)
            return

        # USE LARGEST VALID CONTOUR
        largest_contour, area = max(valid_contours, key=lambda x: x[1])
        
        moments = cv2.moments(largest_contour)
        if moments['m00'] == 0:
            return

        cx = int(moments['m10']/moments['m00'])
        cy = int(moments['m01']/moments['m00'])

        # **DEPTH SAMPLING**
        depth_samples = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                y_sample = max(0, min(height-1, cy + dy))
                x_sample = max(0, min(width-1, cx + dx))
                depth_val = self.depth_image[y_sample, x_sample]
                if depth_val > 0 and not np.isnan(depth_val):
                    depth_samples.append(depth_val)
        
        if not depth_samples:
            self.get_logger().warn("❌ NO VALID DEPTH DATA")
            return
            
        z = np.median(depth_samples) / 1000.0  # Convert mm to meters
        
        # **DETECTION SUCCESS DEBUG**
        self.detection_count += 1
        self.last_detection_time = self.get_clock().now()
        
        fx, fy = self.K[0,0], self.K[1,1]
        cx_k, cy_k = self.K[0,2], self.K[1,2]
        X = (cx - cx_k) * z / fx
        Y = (cy - cy_k) * z / fy
        Z = z
        
        self.get_logger().info(f"✅ DETECTION #{self.detection_count}: Area={area}, Depth={z:.3f}m, Pixel=({cx},{cy})")

        # **PUBLISH AND VISUALIZE**
        square_cam = PointStamped()
        square_cam.header.frame_id = 'camera_color_optical_frame'
        square_cam.header.stamp = rclpy.time.Time().to_msg()
        square_cam.point.x = X
        square_cam.point.y = Y
        square_cam.point.z = Z

        try:
            transform = self.tf_buffer.lookup_transform(
                'link_base', 'camera_color_optical_frame', 
                rclpy.time.Time(), 
                timeout=rclpy.duration.Duration(seconds=0.5)
            )
            
            from tf2_geometry_msgs import do_transform_point
            square_world = do_transform_point(square_cam, transform)
            
            pose_msg = PoseStamped()
            pose_msg.header.frame_id = 'link_base'
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.pose.position = square_world.point
            pose_msg.pose.orientation.w = 1.0
            self.pose_pub.publish(pose_msg)

        except Exception as e:
            self.get_logger().warn(f"TF error: {str(e)[:50]}...")

        # **ENHANCED VISUALIZATION**
        vis = img.copy()
        
        # Draw contour
        cv2.drawContours(vis, [largest_contour], -1, (0, 255, 0), 2)
        
        # Draw center
        color = (0, 0, 255) if z < 0.30 else (255, 0, 0)
        cv2.circle(vis, (cx, cy), 10, color, 2)
        
        # **STATUS TEXT**
        cv2.putText(vis, f"Dist: {z:.2f}m", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(vis, f"Area: {area:.0f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(vis, f"Detections: {self.detection_count}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(vis, f"Mask: {mask_percentage:.1f}%", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        cv2.imshow("Blue Square Detection DEBUG", vis)
        cv2.imshow("Blue Mask", mask)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = BlueSquare3DWorldFinder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
