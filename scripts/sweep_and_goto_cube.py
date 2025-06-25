#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
import copy
import time

JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
SCAN_POSES_RAD = [
    [2.251, -0.105, -1.047, 0.087, 1.082, 2.217],
    [2.915, -1.082, -0.349, 0.175, 1.170, 2.862],
    [-2.653, -0.594, -0.314, 0.070, 0.611, -2.618],
]

def interpolate_joints(pose_a, pose_b, steps):
    """Linearly interpolate between two joint arrays."""
    return [
        [
            pose_a[j] + (pose_b[j] - pose_a[j]) * i / steps
            for j in range(len(pose_a))
        ]
        for i in range(steps + 1)
    ]

class SweepAndGoToCube(Node):
    def __init__(self):
        super().__init__('sweep_and_goto_cube')
        self.cube_found = False
        self.cube_pose = None
        self.cube_sub = self.create_subscription(PoseStamped, '/cube_pose', self.cube_cb, 10)
        self.traj_pub = self.create_publisher(JointTrajectory, '/xarm6_traj_controller/joint_trajectory', 10)
        self.moveit_client = ActionClient(self, MoveGroup, "/move_group")
        self.get_logger().info("Sweep and go node started.")

    def cube_cb(self, msg):
        if not self.cube_found:
            self.get_logger().info("Cube detected! Will go to it after scan.")
            self.cube_found = True
            self.cube_pose = msg

    def send_joint_traj(self, joint_positions, duration=0.5):
        jt = JointTrajectory()
        jt.joint_names = JOINT_NAMES
        pt = JointTrajectoryPoint()
        pt.positions = joint_positions
        pt.time_from_start.sec = int(duration)
        jt.points.append(pt)
        self.traj_pub.publish(jt)

    def center_pose_on_cube(self, pose_stamped, x_offset=0.0, y_offset=0.0):
        pose_centered = copy.deepcopy(pose_stamped)
        pose_centered.pose.position.x += x_offset
        pose_centered.pose.position.y += y_offset
        return pose_centered

    def set_top_down_orientation(self, pose_stamped):
        pose = copy.deepcopy(pose_stamped)
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 1.0
        return pose

    def get_hover_pose(self, pose_stamped, hover_height=0.05):
        hover_pose = copy.deepcopy(pose_stamped)
        hover_pose.pose.position.z += hover_height
        return hover_pose

    def scan_and_goto(self):
        sweep_steps = 10  # Finer sweep = more steps (try 20–50 for your setup)

        # Build the full sweep trajectory with interpolated steps
        full_sweep = []
        for i in range(len(SCAN_POSES_RAD) - 1):
            seg = interpolate_joints(SCAN_POSES_RAD[i], SCAN_POSES_RAD[i+1], sweep_steps)
            full_sweep.extend(seg)
        full_sweep.append(SCAN_POSES_RAD[-1])

        # Sweep and check for cube at each interpolated pose
        for idx, pose in enumerate(SCAN_POSES_RAD):
            if self.cube_found:
                self.get_logger().info("Cube found, breaking sweep!")
                break
            self.get_logger().info(f"Scanning at pose {idx+1}/{len(SCAN_POSES_RAD)}...")
            self.send_joint_traj(pose, duration=1.0)
            # Wait for move to complete, but check for cube every 0.1s
            t_start = time.time()
            move_time = 2.0  # seconds
            while time.time() - t_start < move_time:
                if self.cube_found:
                    self.get_logger().info("Cube found during move, breaking!")
                    break
                rclpy.spin_once(self, timeout_sec=0.1)

        if self.cube_found:
            self.get_logger().info("Centering gripper above the cube.")
            cube_center_pose = self.center_pose_on_cube(self.cube_pose, x_offset=0.025, y_offset=0.025)
            cube_center_pose = self.set_top_down_orientation(cube_center_pose)
            self.get_logger().info(
                f"Centered pose: x={cube_center_pose.pose.position.x:.3f}, "
                f"y={cube_center_pose.pose.position.y:.3f}, z={cube_center_pose.pose.position.z:.3f}"
            )

            self.get_logger().info("Moving to hover pose above the cube.")
            hover_pose = self.get_hover_pose(cube_center_pose, hover_height=0.05)
            self.move_to_pose_with_moveit(hover_pose)
            time.sleep(0.5)

            self.get_logger().info("Now descending to the cube's pose.")
            steps = 5
            hover_z = hover_pose.pose.position.z
            target_z = cube_center_pose.pose.position.z
            for i in range(steps):
                intermediate_pose = copy.deepcopy(cube_center_pose)
                intermediate_pose.pose.position.z = hover_z - ((hover_z - target_z) * (i+1) / steps)
                self.get_logger().info(f"Step {i+1}: Z={intermediate_pose.pose.position.z:.3f}")
                self.move_to_pose_with_moveit(intermediate_pose)
                time.sleep(0.2)
            self.get_logger().info("Descent finished. Ready to pick!")
            while rclpy.ok():
                rclpy.spin_once(self)

    def move_to_pose_with_moveit(self, pose_stamped):
        goal_msg = MoveGroup.Goal()
        goal_msg.request.workspace_parameters.header.frame_id = pose_stamped.header.frame_id
        goal_msg.request.goal_constraints.append(self._pose_constraint(pose_stamped))
        goal_msg.request.group_name = "xarm6"
        self.moveit_client.wait_for_server()
        self.get_logger().info(
            f"Sending MoveGroup goal: x={pose_stamped.pose.position.x:.3f}, "
            f"y={pose_stamped.pose.position.y:.3f}, z={pose_stamped.pose.position.z:.3f}"
        )
        send_goal_future = self.moveit_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self._goal_response_callback)

    def _pose_constraint(self, pose_msg):
        from moveit_msgs.msg import Constraints, PositionConstraint, OrientationConstraint, BoundingVolume
        from shape_msgs.msg import SolidPrimitive

        pos_constraint = PositionConstraint()
        pos_constraint.header = pose_msg.header
        pos_constraint.link_name = "link_tcp"  # CHANGE if your EE link name is different!
        bv = BoundingVolume()
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [0.12, 0.12, 0.12]
        bv.primitives = [primitive]
        bv.primitive_poses = [pose_msg.pose]
        pos_constraint.constraint_region = bv
        pos_constraint.weight = 1.0

        orient_constraint = OrientationConstraint()
        orient_constraint.header = pose_msg.header
        orient_constraint.link_name = "link_tcp"
        orient_constraint.orientation = pose_msg.pose.orientation
        orient_constraint.absolute_x_axis_tolerance = 0.1
        orient_constraint.absolute_y_axis_tolerance = 0.1
        orient_constraint.absolute_z_axis_tolerance = 3.14
        orient_constraint.weight = 1.0

        c = Constraints()
        c.position_constraints = [pos_constraint]
        c.orientation_constraints = [orient_constraint]
        return c

    def _goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by MoveIt!")
            return
        self.get_logger().info("Goal accepted. Waiting for result...")
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self._get_result_callback)

    def _get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f"MoveIt result: {result.error_code.val}")

def main(args=None):
    rclpy.init(args=args)
    node = SweepAndGoToCube()
    node.scan_and_goto()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
