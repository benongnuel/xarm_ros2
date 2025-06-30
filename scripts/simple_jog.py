#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

class SimpleJog(Node):
    def __init__(self):
        super().__init__('simple_jog')
        self.pub = self.create_publisher(TwistStamped, '/servo_server/delta_twist_cmds', 10)
        self.timer = self.create_timer(0.05, self.send_jog)  # 20 Hz

    def send_jog(self):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'link_base'  # or 'base_link' depending on your robot
        msg.twist.linear.x = 0.0  # Move in X (meters/second)
        msg.twist.linear.y = 0.0
        msg.twist.linear.z = 0.5
        msg.twist.angular.x = 0.05
        msg.twist.angular.y = 0.0
        msg.twist.angular.z = 0.0
        self.pub.publish(msg)
        self.get_logger().info('Publishing jog command in X')

def main():
    rclpy.init()
    node = SimpleJog()
    rclpy.spin(node)

if __name__ == '__main__':
    main()

