import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import time
import math

class JointCommander(Node):
    def __init__(self):
        super().__init__('xarm6_joint_commander')
        self.publisher_ = self.create_publisher(JointState, 'joint_states', 10)
        time.sleep(1)  # Give publisher time to setup

    def send_joint_positions(self, joint_names, positions_deg):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = joint_names
        # Convert to radians
        msg.position = [math.radians(x) for x in positions_deg]
        self.publisher_.publish(msg)
        self.get_logger().info(f"Sent joint positions (deg): {positions_deg}")

def main():
    rclpy.init()
    node = JointCommander()

    # --- YOUR JOINT NAMES (for xarm6, no prefix)
    joint_names = [
        'joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6'
    ]

    # --- List of joint angles (degrees), one pose per sub-list
    joint_positions_deg_list = [
        [0, -90, 90, 0, 0, 0],      # Pose 1
        [10, -80, 80, 10, 0, 0],    # Pose 2
    ]

    for positions_deg in joint_positions_deg_list:
        node.send_joint_positions(joint_names, positions_deg)
        time.sleep(2)  # Wait 2 sec between poses

    node.get_logger().info('All joint positions sent. Shutting down...')
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
