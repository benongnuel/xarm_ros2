#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from action_msgs.msg import GoalStatus

from geometry_msgs.msg import PoseStamped, Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, PlanningOptions, CollisionObject
from shape_msgs.msg import SolidPrimitive
import numpy as np
import time
import tf_transformations
from tf2_ros import Buffer, TransformListener
from tf2_geometry_msgs import do_transform_pose

def orientation_quat():
    return tf_transformations.quaternion_from_euler(0, 0, np.pi)

class BlueSquarePbvs(Node):
    def __init__(self):
        super().__init__('blue_square_pbvs')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/blue_square_pose', self.square_cb, 10)
        
        self.sweep_waypoints = [
            (-0.35, -0.15, 0.50), (-0.35,  0.15, 0.50),  # Z=0.50 for ceiling scanning
            ( 0.0,  0.15, 0.50), ( 0.35,  0.15, 0.50),
            ( 0.35, -0.15, 0.50), ( 0.0, -0.15, 0.50),
        ]
        self.sweep_idx = 0
        self.busy = False
        self.visited_squares = []

        self.pbvs_target_pose = None
        self.pbvs_iter = 0
        self.pbvs_max_iters = 25
        self.current_goal_handle = None  # Added for motion cancellation
        self.last_target_update_time = None  # Track when we last got target updates

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=True)
        
        self.planning_scene_pub = self.create_publisher(CollisionObject, '/collision_object', 10)
        
        self.initialized = False
        
        self.init_timer = self.create_timer(1.0, self.initial_start_callback)
        self.get_logger().info("Blue Square PBVS Node created. Initializing...")
        
    def initial_start_callback(self):
        self.init_timer.cancel()
        self.add_ceiling_to_scene()
        self.get_logger().info("Node fully initialized. Starting sweep loop.")
        self.initialized = True
        self.sweep_loop()

    def add_ceiling_to_scene(self):
        ceiling = CollisionObject()
        ceiling.header.frame_id = "link_base"
        ceiling.id = "ceiling"
        primitive = SolidPrimitive(type=SolidPrimitive.BOX, dimensions=[1.5, 1.5, 0.05])
        ceiling.primitives.append(primitive)
        ceiling_pose = Pose()
        ceiling_pose.position.z = 0.85
        ceiling.primitive_poses.append(ceiling_pose)
        ceiling.operation = CollisionObject.ADD
        time.sleep(1)
        self.planning_scene_pub.publish(ceiling)
        self.get_logger().info("Ceiling added to MoveIt planning scene.")

    def square_cb(self, msg):
        if not self.initialized:
            return

        try:
            target_frame = 'link_base'
            source_frame = msg.header.frame_id
            
            transform = self.tf_buffer.lookup_transform(
                target_frame,
                source_frame,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=1.0))

            transformed_pose = PoseStamped()
            transformed_pose.header.frame_id = target_frame
            transformed_pose.header.stamp = msg.header.stamp
            transformed_pose.pose = do_transform_pose(msg.pose, transform)

            self.get_logger().info(f"Transformed square pose from '{source_frame}' to '{target_frame}'.")
        except Exception as e:
            self.get_logger().error(f"Could not transform pose: {e}")
            return
        
        # ALWAYS update the last target update time when we receive a callback
        self.last_target_update_time = self.get_clock().now()
        
        if self.busy:
            # Calculate how much target moved
            if self.pbvs_target_pose is not None:
                old_pos = self.pbvs_target_pose.pose.position
                new_pos = transformed_pose.pose.position
                distance_moved = np.linalg.norm([new_pos.x - old_pos.x, new_pos.y - old_pos.y])
                # If target moved significantly, cancel current motion and replan
                if distance_moved > 0.20:  # 20cm threshold
                    self.get_logger().info(f"Target moved {distance_moved*100:.1f}cm - cancelling current motion")
                    if self.current_goal_handle:
                        self.current_goal_handle.cancel_goal_async()
            
            # Always update target position
            self.pbvs_target_pose = transformed_pose
            self.get_logger().info("PBVS target updated mid-flight.")
            return

        for sq in self.visited_squares:
            dist = np.linalg.norm([transformed_pose.pose.position.x - sq[0], transformed_pose.pose.position.y - sq[1]])
            if dist < 0.1:
                return

        self.busy = True
        self.square_detection_time = time.time()  # Track when we detected the square
        self.get_logger().info("New blue square detected! Stopping sweep and starting PBVS.")
        self.visited_squares.append([transformed_pose.pose.position.x, transformed_pose.pose.position.y])
        
        self.pbvs_target_pose = transformed_pose
        self.pbvs_iter = 0
        self.pbvs_step()

    def sweep_loop(self):
        if self.busy:
            return

        x, y, z = self.sweep_waypoints[self.sweep_idx]
        self.get_logger().info(f"Sweeping to waypoint {self.sweep_idx}: ({x:.2f}, {y:.2f}, {z:.2f})")
        
        sweep_pose = PoseStamped()
        sweep_pose.header.frame_id = 'link_base'
        sweep_pose.pose.position.x, sweep_pose.pose.position.y, sweep_pose.pose.position.z = x, y, z
        quat = orientation_quat()
        sweep_pose.pose.orientation.x, sweep_pose.pose.orientation.y, sweep_pose.pose.orientation.z, sweep_pose.pose.orientation.w = quat
        
        self.sweep_idx = (self.sweep_idx + 1) % len(self.sweep_waypoints)
        self.send_pose_goal_async(sweep_pose, self.sweep_loop_done_callback)

    def sweep_loop_done_callback(self, success):
        if success:
            self.sweep_loop()
        else:
            self.get_logger().error("A sweep motion failed. Retrying loop in 5 seconds.")
            self.create_timer(5.0, self.initial_start_callback)

    def pbvs_step(self):
        if self.pbvs_iter >= self.pbvs_max_iters:
            self.get_logger().warn("PBVS max iterations reached. Resetting.")
            self.reset_state()
            return

        try:
            # FIXED TIMEOUT CHECK - use our own timestamp tracking
            if self.last_target_update_time is not None:
                time_since_last_sighting = self.get_clock().now() - self.last_target_update_time
                # Only check timeout after first few iterations (give it time to start)
                if self.pbvs_iter > 5 and time_since_last_sighting.nanoseconds / 1e9 > 4.0:
                    self.get_logger().warn(f"Target lost (no update in >{time_since_last_sighting.nanoseconds/1e9:.1f}s). Aborting servo.")
                    self.reset_state()
                    return

            target = self.pbvs_target_pose.pose.position
            target_z_eef = min(target.z - 0.01, 0.98)  # Offset to ensure we are above the target
            trans = self.tf_buffer.lookup_transform('link_base', 'link_eef', rclpy.time.Time())
            ee_pos = trans.transform.translation
            
            xy_err = np.linalg.norm([target.x - ee_pos.x, target.y - ee_pos.y])
            z_err = target_z_eef - ee_pos.z

            self.get_logger().info(f"[PBVS {self.pbvs_iter+1}/{self.pbvs_max_iters}] XY_err: {xy_err*100:.1f} cm, Z_err: {z_err*100:.1f} cm")

            if xy_err < 0.1 and abs(z_err) < 0.17:
                elapsed = time.time() - self.square_detection_time if self.square_detection_time else 0.0
                self.get_logger().info(f"Reached target! Time from detection: {elapsed:.2f} seconds, Final XY error: {xy_err*100:.1f} cm")
                self.reset_state()
                return

            next_pose = PoseStamped()
            next_pose.header.frame_id = 'link_base'
            quat = orientation_quat()
            next_pose.pose.orientation.x, next_pose.pose.orientation.y, next_pose.pose.orientation.z, next_pose.pose.orientation.w = quat

            if xy_err > 0.03:
                self.get_logger().info("Phase 1: Aligning in XY plane.")
                step_size = 0.05
                xy_step = min(step_size, xy_err)
                xy_dir = [(target.x - ee_pos.x) / xy_err, (target.y - ee_pos.y) / xy_err]
                
                next_pose.pose.position.x = ee_pos.x + xy_dir[0] * xy_step
                next_pose.pose.position.y = ee_pos.y + xy_dir[1] * xy_step
                next_pose.pose.position.z = ee_pos.z
            else:
                self.get_logger().info("Phase 2: Aligning in Z axis.")
                step_size = 0.10
                z_step = np.sign(z_err) * min(step_size, abs(z_err))

                next_pose.pose.position.x = target.x
                next_pose.pose.position.y = target.y
                next_pose.pose.position.z = ee_pos.z + z_step

            self.pbvs_iter += 1
            self.send_pose_goal_async(next_pose, self.pbvs_step_done_callback)
        except Exception as e:
            self.get_logger().error(f"Exception in PBVS loop: {e}")
            self.reset_state()

    def pbvs_step_done_callback(self, success):
        if success:
            self.pbvs_step()
        else:
            self.get_logger().error("A PBVS step failed. Aborting servo and resetting.")
            self.reset_state()

    def reset_state(self):
        self.get_logger().info("Reset complete. Resuming sweep loop in 3 seconds.")
        self.busy = False
        self.pbvs_target_pose = None
        self.current_goal_handle = None  # Clear goal handle
        self.last_target_update_time = None  # Reset timeout tracking
        self.square_detection_time = None  # Reset square detection time
        self.create_timer(3.0, self.sweep_loop)

    def send_pose_goal_async(self, pose_stamped, done_callback):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            if done_callback: done_callback(False)
            return

        req = MotionPlanRequest(group_name='xarm6', allowed_planning_time=3.0, num_planning_attempts=5)
        pose_stamped.header.stamp = self.get_clock().now().to_msg()

        constraints = Constraints()
        pos_constraint = PositionConstraint(header=pose_stamped.header, link_name='link_eef', weight=1.0)
        pos_constraint.constraint_region.primitives.append(SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.03]))
        pos_constraint.constraint_region.primitive_poses.append(pose_stamped.pose)
        constraints.position_constraints.append(pos_constraint)

        # Add orientation constraints for consistent scanning behavior
        ori_constraint = OrientationConstraint(header=pose_stamped.header, link_name='link_eef', orientation=pose_stamped.pose.orientation, weight=1.0)
        ori_constraint.absolute_x_axis_tolerance = 0.1
        ori_constraint.absolute_y_axis_tolerance = 0.1  
        ori_constraint.absolute_z_axis_tolerance = 3.14
        constraints.orientation_constraints.append(ori_constraint)
        
        req.goal_constraints.append(constraints)

        plan_ops = PlanningOptions(plan_only=False)
        goal_msg = MoveGroup.Goal(request=req, planning_options=plan_ops)

        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(lambda future: self.goal_accepted_callback(future, done_callback))

    def goal_accepted_callback(self, future, done_callback):
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().warn("Goal rejected by MoveGroup.")
                if done_callback: done_callback(False)
                return
            
            self.current_goal_handle = goal_handle  # Store for cancellation
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(lambda future: self.goal_result_callback(future, done_callback))
        except Exception as e:
            self.get_logger().error(f"Error accepting goal: {e}")
            if done_callback: done_callback(False)

    def goal_result_callback(self, future, done_callback):
        self.current_goal_handle = None  # Clear handle when done
        result = future.result()
        status = result.status

        if status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info("Move step was cancelled, replanning to new target.")
            self.pbvs_step()  # Immediately replan to new target
            return

        try:
            moveit_result = result.result
            success = (moveit_result.error_code.val == 1)
            if not success:
                self.get_logger().warn(f"Move failed with error code: {moveit_result.error_code.val}")
            if done_callback: done_callback(success)
        except Exception as e:
            self.get_logger().error(f"Error getting goal result: {e}")
            if done_callback: done_callback(False)

def main(args=None):
    rclpy.init(args=args)
    node = BlueSquarePbvs()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()