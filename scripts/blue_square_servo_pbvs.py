#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TwistStamped
import numpy as np
import tf2_ros

class BlueSquareServoPBVS(Node):
    def __init__(self):
        super().__init__('blue_square_servo_pbvs')
        self.target_pose = None

        # Subscribe to blue square position (in link_base frame)
        self.create_subscription(PoseStamped, '/blue_square_pose', self.pose_callback, 10)
        
        # Publisher to MoveIt Servo
        self.cmd_pub = self.create_publisher(TwistStamped, '/servo_server/delta_twist_cmds', 10)
        
        # TF setup for end-effector pose
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # Set control gains (tune these!)
        self.kp = 1.2     # Proportional gain for how fast to move
        self.max_speed = 0.2   # Max linear velocity [m/s]
        self.z_offset = 0.05   # Stop a bit above the square

        self.timer = self.create_timer(0.05, self.control_loop)  # 20 Hz

    def pose_callback(self, msg):
        # Save latest detected square pose
        self.target_pose = msg

    def control_loop(self):
        if self.target_pose is None:
            return

        # Get the current EE pose (position only)
        try:
            trans = self.tf_buffer.lookup_transform(
                'link_base', 'link_eef', rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.2)
            )
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}")
            return

        # Target and current pose
        tgt = self.target_pose.pose.position
        ee = trans.transform.translation

        # Compute error vector
        dx = tgt.x - ee.x
        dy = tgt.y - ee.y
        dz = (tgt.z + self.z_offset) - ee.z

        # Simple proportional velocity controller
        vx = np.clip(self.kp * dx, -self.max_speed, self.max_speed)
        vy = np.clip(self.kp * dy, -self.max_speed, self.max_speed)
        vz = np.clip(self.kp * dz, -self.max_speed, self.max_speed)

        # Stop if very close (for stability)
        if np.linalg.norm([dx, dy, dz]) < 0.03:
            vx, vy, vz = 0.0, 0.0, 0.0

        cmd = TwistStamped()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = 'link_base'
        cmd.twist.linear.x = vx
        cmd.twist.linear.y = vy
        cmd.twist.linear.z = vz
        # No rotation for now—add if you want orientation control!
        cmd.twist.angular.x = 0.0
        cmd.twist.angular.y = 0.0
        cmd.twist.angular.z = 0.0

        self.cmd_pub.publish(cmd)
        self.get_logger().info(f"PBVS cmd: [{vx:.3f}, {vy:.3f}, {vz:.3f}] | err = {np.linalg.norm([dx,dy,dz]):.3f} m")

def main(args=None):
    rclpy.init(args=args)
    node = BlueSquareServoPBVS()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

