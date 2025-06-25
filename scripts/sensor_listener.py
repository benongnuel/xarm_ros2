#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import WrenchStamped

class FTSensorListener(Node):
    def __init__(self):
        super().__init__('ft_sensor_listener')
        self.create_subscription(
            WrenchStamped,
            '/gazebo/default/UF_ROBOT/link6/wrench',  # Use your actual topic name
            self.ft_callback,
            10
        )

    def ft_callback(self, msg):
        print("Callback triggered!")
        force = msg.wrench.force
        torque = msg.wrench.torque
        self.get_logger().info(
            f"Force: x={force.x:.2f}, y={force.y:.2f}, z={force.z:.2f} | "
            f"Torque: x={torque.x:.2f}, y={torque.y:.2f}, z={torque.z:.2f}"
        )

def main(args=None):
    rclpy.init(args=args)
    node = FTSensorListener()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
