#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, WorkspaceParameters
from shape_msgs.msg import SolidPrimitive
from rclpy.action import ActionClient
import time
import numpy as np
import tf_transformations

def interpolate_pose(pose1, pose2, alpha):
    interp_pose = PoseStamped()
    interp_pose.header = pose1.header

    # Linear interpolation for position
    interp_pose.pose.position.x = (1 - alpha) * pose1.pose.position.x + alpha * pose2.pose.position.x
    interp_pose.pose.position.y = (1 - alpha) * pose1.pose.position.y + alpha * pose2.pose.position.y
    interp_pose.pose.position.z = (1 - alpha) * pose1.pose.position.z + alpha * pose2.pose.position.z

    # SLERP for orientation
    q1 = [
        pose1.pose.orientation.x,
        pose1.pose.orientation.y,
        pose1.pose.orientation.z,
        pose1.pose.orientation.w,
    ]
    q2 = [
        pose2.pose.orientation.x,
        pose2.pose.orientation.y,
        pose2.pose.orientation.z,
        pose2.pose.orientation.w,
    ]
    q_interp = tf_transformations.quaternion_slerp(q1, q2, alpha)
    interp_pose.pose.orientation.x = q_interp[0]
    interp_pose.pose.orientation.y = q_interp[1]
    interp_pose.pose.orientation.z = q_interp[2]
    interp_pose.pose.orientation.w = q_interp[3]

    return interp_pose

class SlerpFindBlueSquare(Node):
    def __init__(self):
        super().__init__('slerp_find_blue_square')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/blue_square_pose', self.pose_cb, 10)
        self.last_pose = None
        self.found_square = False
        self.sweep_idx = 0
        self.sweep_waypoints = [
            (-0.45, -0.15, 0.70),
            (-0.45,  0.15, 0.70),
            ( 0.0,  0.15, 0.70),
            ( 0.45,  0.15, 0.70),
            ( 0.45, -0.15, 0.70),
            ( 0.0, -0.15, 0.70),
        ]
        self.timer = self.create_timer(4.0, self.sweep_motion)

    def pose_cb(self, msg):
        if self.found_square:
            return

        # Approach from above
        above_pose = PoseStamped()
        above_pose.header = msg.header
        above_pose.pose.position.x = msg.pose.position.x
        above_pose.pose.position.y = msg.pose.position.y
        above_pose.pose.position.z = msg.pose.position.z + 0.10  # 10cm above
        quat = tf_transformations.quaternion_from_euler(0, 0, np.pi)
        above_pose.pose.orientation.x = quat[0]
        above_pose.pose.orientation.y = quat[1]
        above_pose.pose.orientation.z = quat[2]
        above_pose.pose.orientation.w = quat[3]

        contact_pose = PoseStamped()
        contact_pose.header = msg.header
        contact_pose.pose.position.x = msg.pose.position.x
        contact_pose.pose.position.y = msg.pose.position.y
        contact_pose.pose.position.z = msg.pose.position.z + 0.01  # 1cm above
        contact_pose.pose.orientation = above_pose.pose.orientation

        steps = 10
        for i in range(steps + 1):
            alpha = i / steps
            interp_pose = interpolate_pose(above_pose, contact_pose, alpha)
            self.send_pose_goal(interp_pose)
            time.sleep(0.2)

        self.found_square = True
        self.get_logger().info("Finished SLERP approach to blue square.")

    def sweep_motion(self):
        if self.found_square:
            return
        x, y, z = self.sweep_waypoints[self.sweep_idx]
        sweep_pose = PoseStamped()
        sweep_pose.header.frame_id = 'link_base'
        sweep_pose.pose.position.x = x
        sweep_pose.pose.position.y = y
        sweep_pose.pose.position.z = z
        quat = tf_transformations.quaternion_from_euler(0, 0, np.pi)
        sweep_pose.pose.orientation.x = quat[0]
        sweep_pose.pose.orientation.y = quat[1]
        sweep_pose.pose.orientation.z = quat[2]
        sweep_pose.pose.orientation.w = quat[3]
        self.get_logger().info(f"Sweeping to waypoint {self.sweep_idx}: ({x:.2f}, {y:.2f}, {z:.2f})")
        self.send_pose_goal(sweep_pose)
        self.sweep_idx = (self.sweep_idx + 1) % len(self.sweep_waypoints)

    def send_pose_goal(self, pose):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            return
        req = MotionPlanRequest()
        req.group_name = 'xarm6'
        req.goal_constraints.append(Constraints())
        req.goal_constraints[0].position_constraints.append(PositionConstraint())
        req.goal_constraints[0].position_constraints[0].header = pose.header
        req.goal_constraints[0].position_constraints[0].link_name = 'link6'
        req.goal_constraints[0].position_constraints[0].constraint_region.primitives.append(
            SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.01]))
        req.goal_constraints[0].position_constraints[0].constraint_region.primitive_poses.append(pose.pose)
        req.goal_constraints[0].position_constraints[0].weight = 1.0

        ori_constraint = OrientationConstraint()
        ori_constraint.header = pose.header
        ori_constraint.link_name = 'link6'
        ori_constraint.orientation = pose.pose.orientation
        ori_constraint.absolute_x_axis_tolerance = 0.1
        ori_constraint.absolute_y_axis_tolerance = 0.1
        ori_constraint.absolute_z_axis_tolerance = 0.1
        ori_constraint.weight = 1.0
        req.goal_constraints[0].orientation_constraints.append(ori_constraint)

        req.workspace_parameters = WorkspaceParameters()

        goal_msg = MoveGroup.Goal()
        goal_msg.request = req
        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.look_around = False
        goal_msg.planning_options.replan = False

        self._action_client.wait_for_server()
        future = self._action_client.send_goal_async(goal_msg)
        self.get_logger().info("Goal sent to MoveIt!")

def main(args=None):
    rclpy.init(args=args)
    node = SlerpFindBlueSquare()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()