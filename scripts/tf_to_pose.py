#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import tf2_ros

class TfToPose(Node):
    def __init__(self):
        super().__init__('tf_to_pose')
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        self.pub = self.create_publisher(PoseStamped, '/ee_pose', 10)
        self.timer = self.create_timer(0.1, self.timer_cb)

    def timer_cb(self):
        try:
            trans = self.tf_buffer.lookup_transform('link_base', 'link_eef', rclpy.time.Time())
            pose = PoseStamped()
            pose.header = trans.header
            pose.pose.position.x = trans.transform.translation.x
            pose.pose.position.y = trans.transform.translation.y
            pose.pose.position.z = trans.transform.translation.z
            pose.pose.orientation = trans.transform.rotation
            self.pub.publish(pose)
        except Exception:
            pass

def main(args=None):
    rclpy.init(args=args)
    node = TfToPose()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
