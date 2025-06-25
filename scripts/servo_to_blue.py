#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TwistStamped
import numpy as np

class ServoToBlueSquare(Node):
    def __init__(self):
        super().__init__('servo_to_blue_square')
        self.target_pose = None
        self.ee_pose = None
        self.Kp = 0.5

        self.create_subscription(PoseStamped, '/blue_square_pose', self.target_cb, 10)
        self.create_subscription(PoseStamped, '/ee_pose', self.ee_cb, 10)  # You need to publish this from TF or MoveIt
        self.cmd_pub = self.create_publisher(TwistStamped, '/servo_node/delta_twist_cmds', 10)

        self.timer = self.create_timer(0.1, self.step)

    def target_cb(self, msg):
        self.target_pose = msg

    def ee_cb(self, msg):
        self.ee_pose = msg

    def step(self):
        if self.target_pose is None or self.ee_pose is None:
            return
        # Compute position error
        dx = self.target_pose.pose.position.x - self.ee_pose.pose.position.x
        dy = self.target_pose.pose.position.y - self.ee_pose.pose.position.y
        dz = self.target_pose.pose.position.z - self.ee_pose.pose.position.z

        # Stop if close enough
        if np.linalg.norm([dx, dy, dz]) < 0.01:
            return

        cmd = TwistStamped()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = 'link_base'  # Make sure this matches your planning frame
        cmd.twist.linear.x = self.Kp * dx
        cmd.twist.linear.y = self.Kp * dy
        cmd.twist.linear.z = self.Kp * dz
        self.cmd_pub.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = ServoToBlueSquare()
    rclpy.spin(node)

if __name__ == '__main__':
    main()