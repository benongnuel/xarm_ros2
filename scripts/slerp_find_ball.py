import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor # Use a multi-threaded executor for TF

from geometry_msgs.msg import PoseStamped, Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint
from shape_msgs.msg import SolidPrimitive
import time
import numpy as np
import tf_transformations
from tf2_ros import Buffer, TransformListener # Import TF2 components
import csv # Import CSV module
import os # To check if file exists

def interpolate_pose(pose1, pose2, alpha):
    interp_pose = PoseStamped()
    interp_pose.header = pose1.header

    # Linear interpolation for position
    interp_pose.pose.position.x = (1 - alpha) * pose1.pose.position.x + alpha * pose2.pose.position.x
    interp_pose.pose.position.y = (1 - alpha) * pose1.pose.position.y + alpha * pose2.pose.position.y
    interp_pose.pose.position.z = (1 - alpha) * pose1.pose.position.z + alpha * pose2.pose.position.z

    # SLERP for orientation
    q1 = [
        pose1.pose.orientation.x, pose1.pose.orientation.y, pose1.pose.orientation.z, pose1.pose.orientation.w,
    ]
    q2 = [
        pose2.pose.orientation.x, pose2.pose.orientation.y, pose2.pose.orientation.z, pose2.pose.orientation.w,
    ]
    q_interp = tf_transformations.quaternion_slerp(q1, q2, alpha)
    interp_pose.pose.orientation.x = q_interp[0]
    interp_pose.pose.orientation.y = q_interp[1]
    interp_pose.pose.orientation.z = q_interp[2]
    interp_pose.pose.orientation.w = q_interp[3]

    return interp_pose

class MoveItPoseGoalClient(Node):
    def __init__(self):
        super().__init__('moveit_pose_goal_client')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/red_ball_pose', self.pose_cb, 10)
        
        self.found_ball = False
        self.sweep_idx = 0
        self.sweep_waypoints = [
            ( 0.3, -0.3, 0.5), ( 0.3,  0.3, 0.5),
            (-0.3,  0.3, 0.5), (-0.3, -0.3, 0.5),
        ]
        self.timer = self.create_timer(5.0, self.sweep_motion)

        self.last_ball_position = None
        self.reset_timer = None
        self.last_ball_pose = None
        self.busy = False

        # --- Additions for error measurement and logging ---
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=True)
        self.log_counter = 0
        self.tool_length = 0.10

    def pose_cb(self, msg):
        if self.busy:
            return

        # Debounce: ignore if we've recently processed a ball
        if self.last_ball_position is not None:
            dist = np.linalg.norm([msg.pose.position.x - self.last_ball_position[0], msg.pose.position.y - self.last_ball_position[1]])
            if dist < 0.1:
                return

        self.busy = True
        self.found_ball = True
        self.last_ball_pose = msg
        self.get_logger().info("New red ball detected! Starting open-loop approach.")

        # Define target pose for the tool tip
        contact_pose = PoseStamped()
        contact_pose.header = msg.header
        contact_pose.pose.position.x = msg.pose.position.x
        contact_pose.pose.position.y = msg.pose.position.y
        contact_pose.pose.position.z = msg.pose.position.z + self.tool_length
        quat = tf_transformations.quaternion_from_euler(0, np.pi, 0)
        contact_pose.pose.orientation.x, contact_pose.pose.orientation.y, contact_pose.pose.orientation.z, contact_pose.pose.orientation.w = quat

        # Send the single goal
        self.send_pose_goal(contact_pose, self.open_loop_done_callback)

    def open_loop_done_callback(self, success):
        if not success:
            self.get_logger().error("Open-loop motion failed.")
            self.reset_state()
            return

        self.get_logger().info("Open-loop approach complete. Measuring final error...")
        time.sleep(0.5) # Give robot a moment to settle before measuring

        try:
            # Get the actual final pose of the end-effector
            trans = self.tf_buffer.lookup_transform('link_base', 'link_eef', rclpy.time.Time())
            ee_pos = trans.transform.translation
            
            # The target was the ball position + tool length
            target_pos = self.last_ball_pose.pose.position
            target_z_eef = target_pos.z + self.tool_length

            # Calculate the final 3D error
            final_error = np.linalg.norm([
                target_pos.x - ee_pos.x,
                target_pos.y - ee_pos.y,
                target_z_eef - ee_pos.z
            ])
            
            self.get_logger().info(f"Final open-loop error: {final_error*100:.2f} cm")
            self.save_slerp_log(final_error * 100)

        except Exception as e:
            self.get_logger().error(f"Could not measure final error: {e}")

        # Start timer to move up and reset
        if self.reset_timer is not None: self.reset_timer.cancel()
        self.reset_timer = self.create_timer(5.0, self.move_up_and_reset)

    def save_slerp_log(self, final_error_cm):
        """Appends the final error to a CSV file."""
        filename = "slerp_final_errors.csv"
        self.log_counter += 1
        file_exists = os.path.isfile(filename)
        
        try:
            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(['run', 'final_error_cm']) # Write header only once
                writer.writerow([self.log_counter, final_error_cm])
            self.get_logger().info(f"Successfully appended error to {filename}")
        except IOError as e:
            self.get_logger().error(f"Could not save log file: {e}")

    def move_up_and_reset(self):
        if self.last_ball_pose is None:
            self.reset_state()
            return
            
        up_pose = PoseStamped()
        up_pose.header = self.last_ball_pose.header
        up_pose.pose.position.x = self.last_ball_pose.pose.position.x
        up_pose.pose.position.y = self.last_ball_pose.pose.position.y
        up_pose.pose.position.z = 0.50 # Move to a safe height

        quat = tf_transformations.quaternion_from_euler(0, np.pi, 0)
        up_pose.pose.orientation.x, up_pose.pose.orientation.y, up_pose.pose.orientation.z, up_pose.pose.orientation.w = quat

        self.get_logger().info("Moving up to a safe height.")
        self.send_pose_goal(up_pose, lambda success: self.reset_state())

    def reset_state(self):
        self.get_logger().info("Resetting state to resume sweep.")
        self.found_ball = False
        self.busy = False
        self.last_ball_position = (
            self.last_ball_pose.pose.position.x,
            self.last_ball_pose.pose.position.y
        )
        self.last_ball_pose = None
        if self.reset_timer is not None:
            self.reset_timer.cancel()
            self.reset_timer = None

    def sweep_motion(self):
        if self.busy:
            return

        x, y, z = self.sweep_waypoints[self.sweep_idx]
        sweep_pose = PoseStamped()
        sweep_pose.header.frame_id = 'link_base'
        sweep_pose.pose.position.x, sweep_pose.pose.position.y, sweep_pose.pose.position.z = x, y, z
        quat = tf_transformations.quaternion_from_euler(0, np.pi, 0)
        sweep_pose.pose.orientation.x, sweep_pose.pose.orientation.y, sweep_pose.pose.orientation.z, sweep_pose.pose.orientation.w = quat

        self.get_logger().info(f"Sweeping to waypoint {self.sweep_idx}: ({x:.2f}, {y:.2f}, {z:.2f})")
        self.send_pose_goal(sweep_pose)
        self.sweep_idx = (self.sweep_idx + 1) % len(self.sweep_waypoints)

    def send_pose_goal(self, pose_stamped, done_callback=None):
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

        goal_msg = MoveGroup.Goal(request=req)
        goal_msg.planning_options.plan_only = False

        send_goal_future = self._action_client.send_goal_async(goal_msg)
        if done_callback:
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
    node = MoveItPoseGoalClient()
    # Use a MultiThreadedExecutor to allow the TF listener to run in the background
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