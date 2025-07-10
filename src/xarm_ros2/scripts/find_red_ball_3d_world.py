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
import tf_transformations

class RedBall3DWorldFinder(Node):
    def __init__(self):
        super().__init__('find_red_ball_3d_world')
        self.bridge = CvBridge()

        # Subscribe to camera topics (RGB, depth, and camera info)
        self.rgb_sub = self.create_subscription(Image, '/color/image_raw', self.rgb_callback, 10)
        self.depth_sub = self.create_subscription(Image, '/aligned_depth_to_color/image_raw', self.depth_callback, 10)
        self.caminfo_sub = self.create_subscription(CameraInfo, '/color/camera_info', self.caminfo_callback, 10)

        self.rgb_image = None
        self.depth_image = None
        self.K = None

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.ball_visible = True
        self.last_no_ball_log_time = self.get_clock().now().seconds_nanoseconds()[0]

        self.pose_pub = self.create_publisher(PoseStamped, '/red_ball_pose', 10)
        self.timer = self.create_timer(0.1, self.process)

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

        # --- Red color mask (red wraps around HSV, so two ranges) ---
        lower_red1 = np.array([0, 120, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 120, 70])
        upper_red2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        # --- Find centroid of red blob ---
        moments = cv2.moments(mask)
        if moments['m00'] == 0:
            now_sec = self.get_clock().now().seconds_nanoseconds()[0]
            if self.ball_visible or (now_sec - self.last_no_ball_log_time) >= 3:
                self.get_logger().warn("Red ball not detected!")
                self.ball_visible = False
                self.last_no_ball_log_time = now_sec
            return
        self.ball_visible = True

        cx = int(moments['m10']/moments['m00'])
        cy = int(moments['m01']/moments['m00'])

        # --- Get depth ---
        z = self.depth_image[cy, cx] / 1000.0
        if z == 0 or np.isnan(z):
            self.get_logger().info("No valid depth at red ball location.")
            return

        fx = self.K[0,0]
        fy = self.K[1,1]
        cx_k = self.K[0,2]
        cy_k = self.K[1,2]

        X = (cx - cx_k) * z / fx
        Y = (cy - cy_k) * z / fy
        Z = z
        self.get_logger().info(f"[Camera] Red ball: X={X:.3f}, Y={Y:.3f}, Z={Z:.3f} m")

        ball_cam = PointStamped()
        ball_cam.header.frame_id = 'camera_color_optical_frame'
        ball_cam.header.stamp.sec = 0
        ball_cam.header.stamp.nanosec = 0
        ball_cam.point.x = X
        ball_cam.point.y = Y
        ball_cam.point.z = Z

        try:
            ball_world = self.tf_buffer.transform(
                ball_cam,
                'link_base',  # Change to your robot's base frame if needed
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
            self.get_logger().info(
                f"[World] Red ball: X={ball_world.point.x:.3f}, Y={ball_world.point.y:.3f}, Z={ball_world.point.z:.3f} m"
            )

            pose_msg = PoseStamped()
            pose_msg.header = ball_world.header
            pose_msg.pose.position = ball_world.point
            max_z = 0.7
            if pose_msg.pose.position.z > max_z:
                pose_msg.pose.position.z = max_z

            # Fixed orientation (identity quaternion)
            pose_msg.pose.orientation.x = 0.0
            pose_msg.pose.orientation.y = 0.0
            pose_msg.pose.orientation.z = 0.0
            pose_msg.pose.orientation.w = 1.0

            self.pose_pub.publish(pose_msg)

        except Exception as e:
            self.get_logger().warn(f"TF2 transform error: {e}")

        vis = img.copy()
        cv2.circle(vis, (cx, cy), 10, (0,0,255), 2)  # Red circle
        cv2.imshow("Red Ball Detection", vis)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = RedBall3DWorldFinder()
    rclpy.spin(node)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
