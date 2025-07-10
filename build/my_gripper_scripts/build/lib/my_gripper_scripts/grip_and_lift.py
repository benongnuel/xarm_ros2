#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import math
import time

def deg2rad(deg):
    return deg * math.pi / 180.0

# Define poses in radians
poses = [
    [deg2rad(1), deg2rad(-58), deg2rad(-27), deg2rad(0), deg2rad(85), deg2rad(1)],       # Pose 1
    [deg2rad(152), deg2rad(20), deg2rad(-104), deg2rad(0), deg2rad(84), deg2rad(152)],   # Pose 2
    [deg2rad(137), deg2rad(-12), deg2rad(-64), deg2rad(0), deg2rad(76), deg2rad(137)],   # Pose 3
    [deg2rad(135), deg2rad(-8), deg2rad(-68), deg2rad(0), deg2rad(76), deg2rad(135)],    # Pose 4
    [deg2rad(135), deg2rad(3), deg2rad(-48), deg2rad(0), deg2rad(44), deg2rad(135)],
    [deg2rad(135), deg2rad(2), deg2rad(-46), deg2rad(0), deg2rad(44), deg2rad(135)],
    [deg2rad(136), deg2rad(1), deg2rad(-47), deg2rad(0), deg2rad(45), deg2rad(136)],
    [deg2rad(136), deg2rad(14), deg2rad(-40), deg2rad(0), deg2rad(26), deg2rad(118)],
]

joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']

class XArmGripDemo(Node):
    def __init__(self):
        super().__init__('xarm_grip_demo')
        self.arm_pub = self.create_publisher(JointTrajectory, '/xarm6_traj_controller/joint_trajectory', 10)
        self.gripper_pub = self.create_publisher(JointTrajectory, '/xarm_gripper_traj_controller/joint_trajectory', 10)
        self.timer = self.create_timer(2.0, self.run_sequence)
        self.sent = False

    def send_arm_pose(self, joint_values, duration=2):
        traj = JointTrajectory()
        traj.joint_names = joint_names
        point = JointTrajectoryPoint()
        point.positions = joint_values
        point.time_from_start.sec = duration
        traj.points = [point]
        self.arm_pub.publish(traj)

    def close_gripper(self, close_rad=deg2rad(23), duration=2):
        traj = JointTrajectory()
        traj.joint_names = ['drive_joint']
        point = JointTrajectoryPoint()
        point.positions = [close_rad]  # 23 deg = 0.401 rad
        point.time_from_start.sec = duration
        traj.points = [point]
        self.gripper_pub.publish(traj)

    def open_gripper(self, open_rad=deg2rad(0), duration=2):
        traj = JointTrajectory()
        traj.joint_names = ['drive_joint']
        point = JointTrajectoryPoint()
        point.positions = [open_rad]  # 0 rad = fully open
        point.time_from_start.sec = duration
        traj.points = [point]
        self.gripper_pub.publish(traj)

    def run_sequence(self):
        if self.sent:
            return
        self.get_logger().info("Opening gripper")
        self.open_gripper(open_rad=deg2rad(0), duration=2)
        time.sleep(2.5)
        # Move through all poses with gripper open
        for idx, pose in enumerate(poses, start=1):
            self.get_logger().info(f"Sending arm to Pose {idx}")
            self.send_arm_pose(pose)
            time.sleep(2.5)
        # Only close the gripper after all poses
        self.get_logger().info("Closing gripper to 23 degrees")
        self.close_gripper(close_rad=deg2rad(23), duration=2)
        time.sleep(2.5)
        self.get_logger().info("Sequence complete! Shutting down node.")
        self.sent = True
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = XArmGripDemo()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
