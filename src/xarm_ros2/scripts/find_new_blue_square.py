#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped, PoseStamped
import cv2
from cv_bridge import CvBridge
import numpy as np
import tf2_ros


class BlueSquare3DWorldFinder(Node):
    def __init__(self):
        super().__init__('find_blue_square_3d_world')
        self.bridge = CvBridge()

        self.rgb_sub = self.create_subscription(Image, '/color/image_raw', self.rgb_callback, 20)
        self.depth_sub = self.create_subscription(Image, '/aligned_depth_to_color/image_raw', self.depth_callback, 20)
        self.caminfo_sub = self.create_subscription(CameraInfo, '/color/camera_info', self.caminfo_callback, 20)

        self.rgb_image = None
        self.depth_image = None
        self.K = None
        self.image_header = None

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.pose_pub = self.create_publisher(PoseStamped, '/blue_square_pose', 20)
        self.timer = self.create_timer(0.2, self.process)  # Slower processing to reduce TF issues

    def caminfo_callback(self, msg):
        if self.K is None:
            self.K = np.array(msg.k).reshape((3,3))
            self.current_cam_frame = msg.header.frame_id
            self.get_logger().info("Camera intrinsics received.")

    def rgb_callback(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.image_header = msg.header

    def depth_callback(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')

    def process(self):
        if self.rgb_image is None or self.depth_image is None or self.K is None or self.image_header is None:
            return

        img = self.rgb_image
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        lower_blue = np.array([100, 150, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        moments = cv2.moments(mask)
        if moments['m00'] == 0:
            return

        cx = int(moments['m10']/moments['m00'])
        cy = int(moments['m01']/moments['m00'])

        # Sample depth from small region around center for robustness
        depth_samples = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                y_sample = max(0, min(self.depth_image.shape[0]-1, cy + dy))
                x_sample = max(0, min(self.depth_image.shape[1]-1, cx + dx))
                depth_val = self.depth_image[y_sample, x_sample]
                if depth_val > 0 and not np.isnan(depth_val):
                    depth_samples.append(depth_val)
        
        if not depth_samples:
            # Fallback: publish 2D pose with fixed Z
            fx, fy = self.K[0,0], self.K[1,1]
            cx_k, cy_k = self.K[0,2], self.K[1,2]
            fallback_z = 0.3  # meters, adjust as needed
            X = (cx - cx_k) * fallback_z / fx
            Y = (cy - cy_k) * fallback_z / fy
            Z = fallback_z

            pose_msg = PoseStamped()
            pose_msg.header.frame_id = 'camera_color_optical_frame'
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.pose.position.x = X
            pose_msg.pose.position.y = Y
            pose_msg.pose.position.z = Z
            pose_msg.pose.orientation.w = 1.0
            self.pose_pub.publish(pose_msg)
            self.get_logger().warn("Depth unavailable, publishing 2D fallback pose.")
            return

        z = np.median(depth_samples) / 1000.0  # Convert mm to meters
        if z == 0 or np.isnan(z) or np.isinf(z):
            # Fallback: publish 2D pose with fixed Z
            fx, fy = self.K[0,0], self.K[1,1]
            cx_k, cy_k = self.K[0,2], self.K[1,2]
            fallback_z = 0.3  # meters, adjust as needed
            X = (cx - cx_k) * fallback_z / fx
            Y = (cy - cy_k) * fallback_z / fy
            Z = fallback_z

            pose_msg = PoseStamped()
            pose_msg.header.frame_id = 'camera_color_optical_frame'
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.pose.position.x = X
            pose_msg.pose.position.y = Y
            pose_msg.pose.position.z = Z
            pose_msg.pose.orientation.w = 1.0
            self.pose_pub.publish(pose_msg)
            self.get_logger().warn("Invalid depth, publishing 2D fallback pose.")
            return
            
       
        fx, fy = self.K[0,0], self.K[1,1]
        cx_k, cy_k = self.K[0,2], self.K[1,2]
        X = (cx - cx_k) * z / fx
        Y = (cy - cy_k) * z / fy
        Z = z
        
        square_cam = PointStamped()
        square_cam.header.frame_id = 'camera_color_optical_frame'
        # **FIX THE TF TIMING ISSUE** - Use Time(0) for latest available transform
        square_cam.header.stamp = rclpy.time.Time().to_msg()
        square_cam.point.x = X
        square_cam.point.y = Y
        square_cam.point.z = Z

        try:
            # Use latest available transform (no specific time)
            transform = self.tf_buffer.lookup_transform(
                'link_base', self.current_cam_frame, 
                rclpy.time.Time(), 
                timeout=rclpy.duration.Duration(seconds=0.5)
            )
            
            # Manual transform instead of tf2_geometry_msgs to avoid timestamp issues
            from tf2_geometry_msgs import do_transform_point
            square_world = do_transform_point(square_cam, transform)
            
            # Detect close/far range
            range_type = "CLOSE" if z < 0.30 else "FAR"
            
            self.get_logger().info(
                f"[{range_type}] Blue square: X={square_world.point.x:.3f}, Y={square_world.point.y:.3f}, Z={square_world.point.z:.3f} m"
            )

            pose_msg = PoseStamped()
            pose_msg.header.frame_id = 'link_base'
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.pose.position = square_world.point
            
            # Clamp Z to avoid ceiling collision
            max_z = 0.9
            if pose_msg.pose.position.z > max_z:
                pose_msg.pose.position.z = max_z

            pose_msg.pose.orientation.w = 1.0
            self.pose_pub.publish(pose_msg)

        except Exception as e:
            # Only log TF errors occasionally to reduce spam
            if hasattr(self, '_last_tf_error'):
                if (self.get_clock().now().nanoseconds - self._last_tf_error) > 2e9:  # 2 seconds
                    self.get_logger().warn(f"TF error: {str(e)[:50]}...")
                    self._last_tf_error = self.get_clock().now().nanoseconds
            else:
                self._last_tf_error = self.get_clock().now().nanoseconds

        # Simple visualization
        vis = img.copy()
        color = (0, 0, 255) if z < 0.30 else (255, 0, 0)  # Red=close, Blue=far
        cv2.circle(vis, (cx, cy), 10, color, 2)
        cv2.putText(vis, f"Dist: {z:.2f}m", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow("Blue Square Detection", vis)
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
