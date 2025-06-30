#!/usr/bin/env python3
# filepath: /home/benongnuel/dev_ws/src/xarm_ros2/scripts/red_ball_servo.py

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TwistStamped
import numpy as np
import tf2_ros

class RedBallServoPBVS(Node):
    def __init__(self):
        super().__init__('red_ball_servo_pbvs')
        self.target_pose = None
        self.sub = self.create_subscription(PoseStamped, '/red_ball_pose', self.cb, 1)
        self.pub = self.create_publisher(TwistStamped, '/servo_server/delta_twist_cmds', 10)
        self.timer = self.create_timer(0.1, self.pbvs_step)  # 10 Hz
        self.Kp = 0.5   # Position gain (tune as needed)
        self.stop_threshold = 0.03  # 3cm
        self.max_vel = 0.1  # m/s
        self.fixed_z = 0.08  # meters above ball to avoid collision

        # For velocity smoothing
        self.last_vx = 0.0
        self.last_vy = 0.0
        self.last_vz = 0.0
        self.alpha = 0.3  # Smoothing factor (0=slow, 1=none)

        # TF buffer/listener for EE pose feedback
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

    def cb(self, msg):
        # Save most recent ball pose (in link_base frame)
        self.target_pose = msg

    def pbvs_step(self):
        if self.target_pose is None:
            return

        # Get current EE pose from TF
        try:
            tf = self.tf_buffer.lookup_transform(
                "link_base", "link_eef", rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.2)
            )
            ee_x = tf.transform.translation.x
            ee_y = tf.transform.translation.y
            ee_z = tf.transform.translation.z
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}")
            return

        # Target position (goal)
        tx = self.target_pose.pose.position.x
        ty = self.target_pose.pose.position.y
        tz = self.target_pose.pose.position.z + self.fixed_z  # Hover above ball

        # Compute error from current EE pose
        dx = tx - ee_x
        dy = ty - ee_y
        dz = tz - ee_z

        error = np.linalg.norm([dx, dy, dz])
        if error < self.stop_threshold:
            self.get_logger().info(f"Red ball reached (err={error:.3f}m), stopping servo.")
            return  # Stop moving

        # Proportional velocity control (saturate to max_vel)
        vx = np.clip(self.Kp * dx, -self.max_vel, self.max_vel)
        vy = np.clip(self.Kp * dy, -self.max_vel, self.max_vel)
        vz = np.clip(self.Kp * dz, -self.max_vel, self.max_vel)

        twist = TwistStamped()
        twist.header.stamp = self.get_clock().now().to_msg()
        twist.header.frame_id = "link_base"
        twist.twist.linear.x = vx
        twist.twist.linear.y = vy
        twist.twist.linear.z = vz
        twist.twist.angular.x = 0.0
        twist.twist.angular.y = 0.0
        twist.twist.angular.z = 0.0

        self.pub.publish(twist)
        self.get_logger().info(
            f"PBVS cmd: [{vx:.3f}, {vy:.3f}, {vz:.3f}] | err = {error:.3f} m"
        )

def main(args=None):
    rclpy.init(args=args)
    node = RedBallServoPBVS()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()