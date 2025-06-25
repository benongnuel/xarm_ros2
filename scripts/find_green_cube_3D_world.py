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

        # (Optional) Reduce log spam: Track last state and time
        self.cube_visible = True
        self.last_no_cube_log_time = self.get_clock().now().seconds_nanoseconds()[0]

        # ----
        # (For Step 5:) Publisher for cube pose (uncomment and use later)
        #from geometry_msgs.msg import PoseStamped
        self.pose_pub = self.create_publisher(PoseStamped, '/cube_pose', 10)
        self.timer = self.create_timer(0.033, self.process)  # Call process() at ~30Hz
    def caminfo_callback(self, msg):
        # Save camera intrinsics (as 3x3 numpy matrix)
        self.K = np.array(msg.k).reshape((3,3))

    def rgb_callback(self, msg):
        # Convert and store latest RGB image
        self.rgb_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        #self.process()  # Try detection
        

    def depth_callback(self, msg):
        # Convert and store latest depth image
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        #self.process()  # Try detection

    def process(self):
        # --- Only continue if we have all needed data ---
        if self.rgb_image is None or self.depth_image is None or self.K is None:
            return

        # Convert RGB image to HSV (for easier color segmentation)
        img = self.rgb_image
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # --- Mask for green color (tweak values as needed for your sim cube) ---
        lower_green = np.array([40, 70, 70])
        upper_green = np.array([80, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # --- Find centroid of green blob using image moments ---
        moments = cv2.moments(mask)
        if moments['m00'] == 0:
            # No cube detected. Only print if state changes, or every 3 seconds.
            now_sec = self.get_clock().now().seconds_nanoseconds()[0]
            if self.cube_visible or (now_sec - self.last_no_cube_log_time) >= 3:
                self.get_logger().warn("Cube not detected!")
                self.cube_visible = False
                self.last_no_cube_log_time = now_sec
            return
        # If we get here, cube is detected!
        self.cube_visible = True

        # --- Centroid in image (pixels) ---
        cx = int(moments['m10']/moments['m00'])
        cy = int(moments['m01']/moments['m00'])

        # --- Restrict detection to center region ---
        img_h, img_w = mask.shape
        # Define a bounding box, e.g., center 40% of the image
        box_w = int(img_w * 0.4)
        box_h = int(img_h * 0.4)
        x_min = (img_w - box_w) // 2
        x_max = x_min + box_w
        y_min = (img_h - box_h) // 2
        y_max = y_min + box_h

        if not (x_min <= cx <= x_max and y_min <= cy <= y_max):
            self.get_logger().info(f"Cube detected at edge (cx={cx}, cy={cy}), ignoring (not in center box)!")
            return  # Skip rest of processing


        # --- Get depth (distance from camera, usually mm, convert to meters) ---
        z = self.depth_image[cy, cx] / 1000.0
        if z == 0 or np.isnan(z):
            self.get_logger().info("No valid depth at cube location.")
            return

        # --- Camera intrinsics: Focal lengths and principal point ---
        fx = self.K[0,0]
        fy = self.K[1,1]
        cx_k = self.K[0,2]
        cy_k = self.K[1,2]

        # --- Convert 2D pixel + depth to 3D position in camera frame (meters) ---
        # See: https://en.wikipedia.org/wiki/Pinhole_camera_model
        X = (cx - cx_k) * z / fx
        Y = (cy - cy_k) * z / fy
        Z = z
        self.get_logger().info(f"[Camera] Green cube: X={X:.3f}, Y={Y:.3f}, Z={Z:.3f} m")

        # --- Transform point from camera frame to world/robot base frame ---
        cube_cam = PointStamped()
        cube_cam.header.frame_id = 'camera_color_optical_frame'  # Your camera's optical frame
        cube_cam.header.stamp.sec = 0  # Use latest transform available
        cube_cam.header.stamp.nanosec = 0
        cube_cam.point.x = X
        cube_cam.point.y = Y
        cube_cam.point.z = Z

        try:
            cube_world = self.tf_buffer.transform(
                cube_cam,
                'link_base',  # Set to your base/world frame as needed. use the camera frame, not gripper, lookout transform.
                timeout=rclpy.duration.Duration(seconds=1.0)
            )
            self.get_logger().info(
                f"[World] Green cube: X={cube_world.point.x:.3f}, Y={cube_world.point.y:.3f}, Z={cube_world.point.z:.3f} m"
            )

            # --- (For Step 5) Publish world position as a PoseStamped ---
            #from geometry_msgs.msg import PoseStamped
            pose_msg = PoseStamped()
            pose_msg.header = cube_world.header
            pose_msg.pose.position = cube_world.point
            pose_msg.pose.orientation.w = 1.0  # No orientation
            self.pose_pub.publish(pose_msg)

        except Exception as e:
            self.get_logger().warn(f"TF2 transform error: {e}")

        # --- Visualization for debugging ---
        vis = img.copy()
        cv2.circle(vis, (cx, cy), 10, (0,0,255), 2)
        cv2.imshow("Green Cube Detection", vis)
        cv2.waitKey(1)

def main(args=None):
    rclpy.init(args=args)
    node = GreenCube3DWorldFinder()
    rclpy.spin(node)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
