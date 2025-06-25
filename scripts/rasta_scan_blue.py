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
            (-0.4, -0.15, 0.60),
            (-0.4,  0.15, 0.60),
            ( 0.0,  0.15, 0.60),
            ( 0.4,  0.15, 0.60),
            ( 0.4, -0.15, 0.60),
            ( 0.0, -0.15, 0.60),
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
            return  # Ignore all vision while busy with approach

        target_frame = 'link_base'
        pose_in_base = PoseStamped()
        try:
            if msg.header.frame_id != target_frame:
                from tf2_ros import LookupException, ConnectivityException, ExtrapolationException, TransformException
                for _ in range(20):
                    try:
                        pose_in_base = self.tf_buffer.transform(msg, target_frame, timeout=rclpy.duration.Duration(seconds=0.1))
                        break
                    except (LookupException, ConnectivityException, ExtrapolationException, TransformException):
                        time.sleep(0.1)
                else:
                    self.get_logger().warn(f"TF transform from {msg.header.frame_id} to {target_frame} not available after retries.")
                    return
            else:
                pose_in_base = msg
        except Exception as e:
            self.get_logger().warn(f"TF transform failed: {e}")
            return

        # Check if this square is already visited
        for sq in self.visited_squares:
            dist = np.linalg.norm([
                pose_in_base.pose.position.x - sq[0],
                pose_in_base.pose.position.y - sq[1],
                pose_in_base.pose.position.z - sq[2]
            ])
            if dist < 0.05:  # 5cm tolerance
                return  # Already visited, ignore

        try:
            trans = self.tf_buffer.lookup_transform(
                target_frame, 'link_eef', rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.1))
            ee_pos = trans.transform.translation
            self.get_logger().info(
                f"Detected square at ({pose_in_base.pose.position.x:.3f}, {pose_in_base.pose.position.y:.3f}, {pose_in_base.pose.position.z:.3f})"
            )
            self.get_logger().info(
                f"End effector at ({ee_pos.x:.3f}, {ee_pos.y:.3f}, {ee_pos.z:.3f})"
            )
            ee_dist = np.linalg.norm([
                pose_in_base.pose.position.x - ee_pos.x,
                pose_in_base.pose.position.y - ee_pos.y,
                pose_in_base.pose.position.z - ee_pos.z
            ])
            self.get_logger().info(f"EE distance to square: {ee_dist:.3f} m")

            # Lock the pose and approach if in range
            if ee_dist < 0.20:
                self.locked_square_pose = pose_in_base
                self.get_logger().info("Locked square pose for approach.")
                self.visited_squares.append([
                    pose_in_base.pose.position.x,
                    pose_in_base.pose.position.y,
                    pose_in_base.pose.position.z
                ])
                self.busy = True
                self.last_square_pose = pose_in_base
                self.get_logger().info("Within 20cm of square, starting blind incremental approach.")
                self.move_blind_until_contact(steps=3, step_size=0.05)
                return

        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}")

    def move_blind_until_contact(self, steps=10, step_size=0.01):
        from copy import deepcopy

        pose = deepcopy(self.last_square_pose)
        quat = orientation_quat()
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]

        for i in range(steps):
            pose.pose.position.z += step_size
            self.get_logger().info(f"Blind step {i+1}/{steps}: Moving up by {step_size*100:.1f} cm")
            self.send_pose_goal(pose)
            time.sleep(1.0)

        self.get_logger().info("Blind approach finished, holding for 10 seconds.")
        if self.hold_timer:
            self.hold_timer.cancel()
        self.hold_timer = self.create_timer(10.0, self.reset_state)

        try:
            trans = self.tf_buffer.lookup_transform(
                'link_base', 'link_eef', rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.1))
            ee_pos = trans.transform.translation
            target = self.last_square_pose.pose.position

            self.get_logger().info(f"EE frame: link_eef in link_base: ({ee_pos.x:.3f}, {ee_pos.y:.3f}, {ee_pos.z:.3f})")
            self.get_logger().info(f"Target frame: ({target.x:.3f}, {target.y:.3f}, {target.z:.3f})")

            xy_offset = np.linalg.norm([
                target.x - ee_pos.x,
                target.y - ee_pos.y
            ])
            z_offset = abs(target.z - ee_pos.z)
            xyz_offset = np.linalg.norm([
                target.x - ee_pos.x,
                target.y - ee_pos.y,
                target.z - ee_pos.z
            ])
            self.get_logger().info(
                f"Alignment after approach: XY offset = {xy_offset*100:.1f} cm, Z offset = {z_offset*100:.1f} cm, XYZ distance = {xyz_offset*100:.1f} cm"
            )
            # --- Final position log like PBVS ---
            self.get_logger().info(
                f"Final position: x={ee_pos.x:.3f}, y={ee_pos.y:.3f}, z={ee_pos.z:.3f}"
            )
            self.get_logger().info(
                f"Target position: x={target.x:.3f}, y={target.y:.3f}, z={target.z:.3f}"
            )
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed after approach: {e}")

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
    node = BlueSquareSweep()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()