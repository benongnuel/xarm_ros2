#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import PoseStamped, Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, PlanningOptions
from shape_msgs.msg import SolidPrimitive
import numpy as np
import tf_transformations
from tf2_ros import Buffer, TransformListener
import csv # Import the CSV module

def orientation_quat():
    # Pointing straight down
    return tf_transformations.quaternion_from_euler(0, np.pi, 0)

class VisualServoRedBall(Node):
    def __init__(self):
        super().__init__('visual_servo_red_ball')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/red_ball_pose', self.ball_cb, 10)
        
        self.sweep_waypoints = [
            ( 0.3, -0.3, 0.5), ( 0.3,  0.3, 0.5),
            (-0.3,  0.3, 0.5), (-0.3, -0.3, 0.5),
        ]
        self.sweep_idx = 0
        self.busy = False
        self.visited_balls = []
        self.tool_length = 0.10

        self.pbvs_target_pose = None
        self.pbvs_iter = 0
        self.pbvs_max_iters = 20

        # --- Additions for data logging ---
        self.error_log = []
        self.pbvs_start_time = None
        self.log_counter = 0 # To create unique filenames

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=True)
        
        self.init_timer = self.create_timer(1.0, self.initial_start_callback)
        self.get_logger().info("Visual Servoing Node created. Initializing...")

    def initial_start_callback(self):
        """A true one-shot callback to start the main control loop."""
        self.init_timer.cancel()
        self.get_logger().info("Node initialized. Starting sweep loop.")
        self.sweep_loop()

    def ball_cb(self, msg):
        if self.busy:
            return

        for ball_pos in self.visited_balls:
            dist = np.linalg.norm([msg.pose.position.x - ball_pos[0], msg.pose.position.y - ball_pos[1]])
            if dist < 0.1:
                return

        self.busy = True
        self.get_logger().info(f"New red ball detected! Stopping sweep and starting PBVS.")
        self.visited_balls.append([msg.pose.position.x, msg.pose.position.y])
        
        # --- Reset and start logging for this new task ---
        self.error_log = []
        self.pbvs_start_time = self.get_clock().now()
        
        self.pbvs_target_pose = msg
        self.pbvs_iter = 0
        self.pbvs_step()

    def sweep_loop(self):
        """The main asynchronous loop for sweeping. It calls itself in the done_callback."""
        if self.busy:
            self.get_logger().info("Sweep loop paused because a ball is being handled.")
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
            self.reset_state_after_pbvs()
            return

        try:
            target = self.pbvs_target_pose.pose.position
            target_z_eef = target.z + self.tool_length
            trans = self.tf_buffer.lookup_transform('link_base', 'link_eef', rclpy.time.Time())
            ee_pos = trans.transform.translation
            xy_err = np.linalg.norm([target.x - ee_pos.x, target.y - ee_pos.y])
            z_err = target_z_eef - ee_pos.z

            # --- Log the current error data ---
            now = (self.get_clock().now() - self.pbvs_start_time).nanoseconds / 1e9
            total_error = np.sqrt(xy_err**2 + z_err**2)
            self.error_log.append((now, total_error * 100)) # Log time and error in cm

            self.get_logger().info(f"[PBVS {self.pbvs_iter+1}/{self.pbvs_max_iters}] XY_err: {xy_err*100:.1f} cm, Z_err: {z_err*100:.1f} cm")

            if xy_err < 0.01 and abs(z_err) < 0.01:
                self.get_logger().info("Target reached. Servoing complete.")
                self.save_log() # --- Save the log to a file ---
                self.reset_state_after_pbvs()
                return

            step_size = 0.08
            xy_step = min(step_size, xy_err)
            z_step = np.sign(z_err) * min(step_size, abs(z_err))
            xy_dir = [(target.x - ee_pos.x) / xy_err, (target.y - ee_pos.y) / xy_err] if xy_err > 1e-6 else [0, 0]

            next_pose = PoseStamped()
            next_pose.header.frame_id = 'link_base'
            next_pose.pose.position.x = ee_pos.x + xy_dir[0] * xy_step
            next_pose.pose.position.y = ee_pos.y + xy_dir[1] * xy_step
            next_pose.pose.position.z = ee_pos.z + z_step
            quat = orientation_quat()
            next_pose.pose.orientation.x, next_pose.pose.orientation.y, next_pose.pose.orientation.z, next_pose.pose.orientation.w = quat

            self.pbvs_iter += 1
            self.send_pose_goal_async(next_pose, self.pbvs_step_done_callback)
        except Exception as e:
            self.get_logger().error(f"Exception in PBVS loop: {e}")
            self.reset_state_after_pbvs()

    def save_log(self):
        """Saves the current error log to a unique CSV file."""
        filename = f"error_log_{self.log_counter}.csv"
        self.log_counter += 1
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['time_s', 'error_cm']) # Write header
                writer.writerows(self.error_log)
            self.get_logger().info(f"Successfully saved log to {filename}")
        except IOError as e:
            self.get_logger().error(f"Could not save log file: {e}")

    def pbvs_step_done_callback(self, success):
        if success:
            self.pbvs_step()
        else:
            self.get_logger().error("A PBVS step failed. Aborting servo and resetting.")
            self.reset_state_after_pbvs()

    def reset_state_after_pbvs(self):
        self.get_logger().info("Moving up to a safe height before resuming sweep.")
        try:
            trans = self.tf_buffer.lookup_transform('link_base', 'link_eef', rclpy.time.Time())
            current_pos = trans.transform.translation
            
            up_pose = PoseStamped()
            up_pose.header.frame_id = 'link_base'
            up_pose.pose.position.x = current_pos.x
            up_pose.pose.position.y = current_pos.y
            up_pose.pose.position.z = 0.50
            quat = orientation_quat()
            up_pose.pose.orientation.x, up_pose.pose.orientation.y, up_pose.pose.orientation.z, up_pose.pose.orientation.w = quat
            self.send_pose_goal_async(up_pose, self.reset_done_callback)
        except Exception as e:
            self.get_logger().error(f"Could not get current pose for reset: {e}. Retrying.")
            self.create_timer(5.0, self.initial_start_callback)

    def reset_done_callback(self, success):
        self.get_logger().info("Reset complete. Resuming sweep loop.")
        self.busy = False
        if success:
            self.sweep_loop()
        else:
            self.get_logger().error("Failed to move to reset pose. Retrying in 5 seconds.")
            self.create_timer(5.0, self.initial_start_callback)

    def send_pose_goal_async(self, pose_stamped, done_callback):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            if done_callback: done_callback(False)
            return

        req = MotionPlanRequest(group_name='xarm6', allowed_planning_time=5.0, num_planning_attempts=10)
        pose_stamped.header.stamp = self.get_clock().now().to_msg()

        constraints = Constraints()
        pos_constraint = PositionConstraint(header=pose_stamped.header, link_name='link_eef', weight=1.0)
        pos_constraint.constraint_region.primitives.append(SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.01]))
        pos_constraint.constraint_region.primitive_poses.append(pose_stamped.pose)
        constraints.position_constraints.append(pos_constraint)
        ori_constraint = OrientationConstraint(header=pose_stamped.header, link_name='link_eef', orientation=pose_stamped.pose.orientation, weight=1.0)
        ori_constraint.absolute_x_axis_tolerance = 0.1
        ori_constraint.absolute_y_axis_tolerance = 0.1
        ori_constraint.absolute_z_axis_tolerance = 0.1
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
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(lambda future: self.goal_result_callback(future, done_callback))
        except Exception as e:
            self.get_logger().error(f"Error accepting goal: {e}")
            if done_callback: done_callback(False)

    def goal_result_callback(self, future, done_callback):
        try:
            result = future.result().result
            success = (result.error_code.val == 1)
            if not success:
                self.get_logger().warn(f"Move failed with error code: {result.error_code.val}")
            if done_callback: done_callback(success)
        except Exception as e:
            self.get_logger().error(f"Error getting goal result: {e}")
            if done_callback: done_callback(False)

def main(args=None):
    rclpy.init(args=args)
    node = VisualServoRedBall()
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