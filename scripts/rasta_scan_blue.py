#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Pose
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, WorkspaceParameters
from shape_msgs.msg import SolidPrimitive
import numpy as np
import time
import tf_transformations
from moveit_msgs.msg import CollisionObject

def orientation_quat():
    # Facing downwards (for ceiling)
    return tf_transformations.quaternion_from_euler(0, 0, np.pi)

class BlueSquareSweep(Node):
    def __init__(self):
        super().__init__('blue_square_sweep')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/blue_square_pose', self.square_cb, 10)
        self.sweep_waypoints = [
            (-0.15, 0.0, 0.88),
        ]
        self.sweep_idx = 0
        self.timer = self.create_timer(4.0, self.sweep_motion)
        self.hold_timer = None
        self.last_square_pose = None
        self.locked_square_pose = None
        self.busy = False  # Prevents retriggering
        self.visited_squares = []  # Track visited squares

        self.add_ceiling_to_scene()

        from tf2_ros import Buffer, TransformListener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=True)

    def add_ceiling_to_scene(self):
        ceiling = CollisionObject()
        ceiling.header.frame_id = "link_base"
        ceiling.id = "ceiling"
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [1.0, 1.5, 0.05]
        ceiling.primitives = [primitive]
        ceiling_pose = Pose()
        ceiling_pose.position.x = 0.0
        ceiling_pose.position.y = 0.0
        ceiling_pose.position.z = 1.0
        ceiling_pose.orientation.w = 1.0
        ceiling.primitive_poses = [ceiling_pose]
        ceiling.operation = CollisionObject.ADD

        self.planning_scene_pub = self.create_publisher(CollisionObject, '/collision_object', 10)
        time.sleep(1)
        self.planning_scene_pub.publish(ceiling)
        self.get_logger().info("Ceiling added to MoveIt planning scene.")

    def square_cb(self, msg):
        if self.busy:
            return  # Ignore if already moving

        # Always move to the fixed blue square pose
        target_pose = PoseStamped()
        target_pose.header.frame_id = 'link_base'
        target_pose.pose.position.x = -0.25
        target_pose.pose.position.y = 0.0
        target_pose.pose.position.z = 0.95
        quat = orientation_quat()
        target_pose.pose.orientation.x = quat[0]
        target_pose.pose.orientation.y = quat[1]
        target_pose.pose.orientation.z = quat[2]
        target_pose.pose.orientation.w = quat[3]

        self.get_logger().info("Blue square detected! Moving to fixed pose (-0.25, 0, 0.97)")
        self.busy = True
        self.send_pose_goal(target_pose)

    def reset_state(self):
        self.get_logger().info("Hold finished, resuming sweep and unlocking pose.")
        self.busy = False
        self.last_square_pose = None
        self.locked_square_pose = None
        if self.hold_timer:
            self.hold_timer.cancel()
            self.hold_timer = None

    def sweep_motion(self):
        if self.busy:
            return
        x, y, z = self.sweep_waypoints[self.sweep_idx]
        sweep_pose = PoseStamped()
        sweep_pose.header.frame_id = 'link_base'
        sweep_pose.pose.position.x = x
        sweep_pose.pose.position.y = y
        sweep_pose.pose.position.z = z
        quat = orientation_quat()
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
        req.goal_constraints[0].position_constraints[0].link_name = 'link_eef'
        req.goal_constraints[0].position_constraints[0].constraint_region.primitives.append(
            SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.01]))
        req.goal_constraints[0].position_constraints[0].constraint_region.primitive_poses.append(pose.pose)
        req.goal_constraints[0].position_constraints[0].weight = 1.0

        ori_constraint = OrientationConstraint()
        ori_constraint.header = pose.header
        ori_constraint.link_name = 'link_eef'
        ori_constraint.orientation = pose.pose.orientation
        ori_constraint.absolute_x_axis_tolerance = 0.3
        ori_constraint.absolute_y_axis_tolerance = 0.3
        ori_constraint.absolute_z_axis_tolerance = 3.14
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
    node = BlueSquareSweep()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()