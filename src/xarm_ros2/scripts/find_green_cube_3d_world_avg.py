#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped, PoseStamped
import cv2
from cv_bridge import CvBridge
import numpy as np
import tf2_ros
import tf2_geometry_msgs  # Needed for transform() of PointStamped

class GreenCube3DWorldFinder(Node):
    def __init__(self):
        super().__init__('find_green_cube_3d_world')
        self.bridge = CvBridge()

        # Subscribe to camera topics (RGB, depth, and camera info)
        self.rgb_sub = self.create_subscription(Image, '/color/image_raw', self.rgb_callback, 10)
        self.depth_sub = self.create_subscription(Image, '/aligned_depth_to_color/image_raw', self.depth_callback, 10)
        self.caminfo_sub = self.create_subscription(CameraInfo, '/color/camera_info', self.caminfo_callback, 10)

        # Variables to store the latest images and camera parameters
        self.rgb_image = None
        self.depth_image = None
        self.K = None  # Camera intrinsic matrix

        # TF2 listener for coordinate transforms
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # For position averaging
        self.last_positions = []
        self.smoothing_N = 5  # Change this for longer/shorter averaging

        self.pose_pub = self.create_publisher(PoseStamped, '/cube_pose', 10)
        self.timer = self.create_timer(0.033, self.process)  # Call process() at ~30Hz

        self.cube_visible = True
        self.last_no_cube_log_time = self.get_clock().now().seconds_nanoseconds()[0]

    def caminfo_callback(self, msg):
        self.K = np.array(msg.k).reshape((3,3))

    def rgb_callback(self, msg):
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def depth_callback(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')

    def process(self):
        if self.rgb_image is None or self.depth_image is None or self.K is None:
            return

        img = self.rgb_image
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_green = np.array([40, 70, 70])
        upper_green = np.array([80, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        moments = cv2.moments(mask)
        if moments['m00'] == 0:
            now_sec = self.get_clock().now().seconds_nanoseconds()[0]
            if self.cube_visible or (now_sec - self.last_no_cube_log_time) >= 3:
                self.get_logger().warn("Cube not detected!")
                self.cube_visible = False
                self.last_no_cube_log_time = now_sec
            self.last_positions = []  # Clear buffer if no cube seen
            return

        self.cube_visible = True
        cx = int(moments['m10']/moments['m00'])
        cy = int(moments['m01']/moments['m00'])

        z = self.depth_image[cy, cx] / 1000.0
        if z == 0 or np.isnan(z):
            self.get_logger().info("No valid depth at cube location.")
            return

        fx = self.K[0,0]
        fy = self.K[1,1]
        cx_k = self.K[0,2]
        cy_k = self.K[1,2]

        X = (cx - cx_k) * z / fx
        Y = (cy - cy_k) * z / fy
        Z = z

        # Log every reading
        self.get_logger().info(f"Centroid: ({cx},{cy}), Depth: {z:.3f}m | [Camera] Green cube: X={X:.3f}, Y={Y:.3f}, Z={Z:.3f}m")

        # Position averaging
        self.last_positions.append([X, Y, Z])
        if len(self.last_positions) > self.smoothing_N:
            self.last_positions.pop(0)

        if len(self.last_positions) < self.smoothing_N:
            return  # Wait until buffer is full

        avg_pos = np.mean(self.last_positions, axis=0)
        X, Y, Z = avg_pos

        cube_cam = PointStamped()
        cube_cam.header.frame_id = 'camera_color_optical_frame'
        cube_cam.header.stamp.sec = 0  # Latest available
        cube_cam.header.stamp.nanosec = 0
        cube_cam.point.x = float(X)
        cube_cam.point.y = float(Y)
        cube_cam.point.z = float(Z)

        try:
            cube_world = self.tf_buffer.transform(
                cube_cam,
                'link_base',  # Or your correct base frame
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
            self.get_logger().info(
                f"[World][AVG {self.smoothing_N}] Green cube: X={cube_world.point.x:.3f}, Y={cube_world.point.y:.3f}, Z={cube_world.point.z:.3f}m"
            )
            pose_msg = PoseStamped()
            pose_msg.header = cube_world.header
            pose_msg.pose.position = cube_world.point
            pose_msg.pose.orientation.w = 1.0
            self.pose_pub.publish(pose_msg)
        except Exception as e:
            self.get_logger().warn(f"TF2 transform error: {e}")

        vis = img.copy()
        cv2.circle(vis, (cx, cy), 10, (0,0,255), 2)
        cv2.imshow("Green Cube Detection (AVG)", vis)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = GreenCube3DWorldFinder()
    rclpy.spin(node)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
