#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TwistStamped, Pose 
import numpy as np
import tf2_ros
import time
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, PlanningOptions
from shape_msgs.msg import SolidPrimitive
from tf_transformations import quaternion_from_euler, quaternion_matrix
from copy import deepcopy
from moveit_msgs.msg import CollisionObject
from tf2_geometry_msgs.tf2_geometry_msgs import do_transform_pose

class HybridServoPlan(Node):
    def __init__(self):
        super().__init__('hybrid_servo_plan')
        self.state = 'sweep'
        self.sweep_poses = [
            (0.3, -0.3, 0.5), (0.3, 0.3, 0.5),
            (-0.3, 0.3, 0.5), (-0.3, -0.3, 0.5),
        ]
        self.sweep_idx = 0
        self.move_in_progress = False

        self.final_errors = []  # Store final XY errors for each servo session
        self.final_times = []    # Store final times for each servo session

        self.planning_scene_pub = self.create_publisher(CollisionObject, '/collision_object', 10)

        self.timer_init = self.create_timer(1.0, self.delayed_init)

        # --- PATCH: Target Lock, Filtering ---
        self.filtered_target_pose = None  # Smoothed vision pose
        self.locked_target_pose = None    # The pose we commit to
        self.lock_on_time = 0.0
        self.lock_tolerance = 0.25      # How far target must move to break lock
        self.lock_reset_time = 10.0       # How long we tolerate vision loss

        self.filter_alpha = 0.3           # Filtering smoothness (0: slow, 1: fast)
        self.deadzone = 0.01               # Do not servo if closer than 1cm

        self.last_detection_time = time.time()
        self.last_servo_to_plan_time = 0.0
        self.last_error = 999.0
        self.error_not_decreasing_count = 0.0
        self.servo_stuck_count = 0.0

        # Hold logic params
        self.hold_start_time = None  # When we start holding position
        self.hold_distance = 0.15   # meters (set this to what you want, e.g. 0.25)
        self.hold_margin = 0.002     # meters, how close to hold
        self.hold_duration = 10.0    # seconds to hold when close

        # Safe home/escape pose (define this clearly for your arm!)
        self.home_pose = (0.0, 0.0, 0.5, 10*np.pi/180, 0.0, np.pi)  # (x, y, z, roll, pitch, yaw)
        self.escape_pose = None

        # Subscribers/publishers
        self.create_subscription(PoseStamped, '/blue_square_pose', self.pose_callback, 10)
        self.cmd_pub = self.create_publisher(TwistStamped, '/servo_server/delta_twist_cmds', 10)

        # TF for EE pose
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # PBVS params
        self.kp = 1.0
        self.max_speed = 0.12
        self.z_offset = 0.05
        self.servo_to_plan_thresh = 0.015
        self.servo_to_plan_hysteresis = 0.03

        self.timer = self.create_timer(0.05, self.main_loop)  # 20 Hz

        # MoveIt action client
        self._action_client = ActionClient(self, MoveGroup, 'move_action')

        # Orientation offset for overhead
        self.approach_tilt_rad = np.deg2rad(10)

    def delayed_init(self):
        self.add_ceiling_to_scene()
        self.timer_init.cancel()  # Run only once


    def add_ceiling_to_scene(self):
        ceiling = CollisionObject()
        ceiling.header.frame_id = 'link_base'
        ceiling.id = 'ceiling'
        ceiling.operation = CollisionObject.ADD
        ceiling.primitives.append(
            SolidPrimitive(type=SolidPrimitive.BOX, dimensions=[1.5, 1.0, 0.1])
        )
        pose = Pose()
        pose.position.x = 0.0
        pose.position.y = 0.0
        pose.position.z = 0.85  # Set ceiling height above workspace
        pose.orientation.w = 1.0
        ceiling.primitive_poses.append(pose)
        self.planning_scene_pub.publish(ceiling)
        self.get_logger().info("Ceiling added to planning scene.")

    # --- PATCH: Vision pose filter + lock-on ---
    def pose_callback(self, msg):
        now = time.time()

        # Low-pass filter for noisy vision
        if self.filtered_target_pose is None:
            self.filtered_target_pose = deepcopy(msg)
        else:
            self.filtered_target_pose.pose.position.x = (
                self.filter_alpha * msg.pose.position.x +
                (1 - self.filter_alpha) * self.filtered_target_pose.pose.position.x
            )
            self.filtered_target_pose.pose.position.y = (
                self.filter_alpha * msg.pose.position.y +
                (1 - self.filter_alpha) * self.filtered_target_pose.pose.position.y
            )
            self.filtered_target_pose.pose.position.z = (
                self.filter_alpha * msg.pose.position.z +
                (1 - self.filter_alpha) * self.filtered_target_pose.pose.position.z
            )
            # Optionally filter orientation (here we just use latest, can slerp if you want)
            self.filtered_target_pose.pose.orientation = msg.pose.orientation

        # Lock-on: Commit to a goal until it moves a lot or we've lost vision for a long time
        if self.locked_target_pose is None:
            self.locked_target_pose = deepcopy(self.filtered_target_pose)
            self.lock_on_time = now
        else:
            dx = self.filtered_target_pose.pose.position.x - self.locked_target_pose.pose.position.x
            dy = self.filtered_target_pose.pose.position.y - self.locked_target_pose.pose.position.y
            dz = self.filtered_target_pose.pose.position.z - self.locked_target_pose.pose.position.z
            dist = np.linalg.norm([dx, dy, dz])
            # Relock if the target shifts too far (or after a long time)
            if dist > self.lock_tolerance or (now - self.lock_on_time) > 5.0:
                self.locked_target_pose = deepcopy(self.filtered_target_pose)
                self.lock_on_time = now
        self.last_detection_time = now

    def send_pose_goal_async(self, pose_stamped):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            return

        req = MotionPlanRequest(group_name='xarm6', allowed_planning_time=3.0, num_planning_attempts=5)
        pose_stamped.header.stamp = self.get_clock().now().to_msg()

        constraints = Constraints()
        pos_constraint = PositionConstraint(header=pose_stamped.header, link_name='link6', weight=1.0)
        pos_constraint.constraint_region.primitives.append(SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.015]))
        pos_constraint.constraint_region.primitive_poses.append(pose_stamped.pose)
        constraints.position_constraints.append(pos_constraint)

        # Orientation: EEF z-axis "almost down" for overhead work (slightly tilted)
        q = pose_stamped.pose.orientation
        if q.x == 0.0 and q.y == 0.0 and q.z == 0.0 and q.w == 0.0:
            qx, qy, qz, qw = quaternion_from_euler(self.approach_tilt_rad, 0, np.pi)
            pose_stamped.pose.orientation.x = qx
            pose_stamped.pose.orientation.y = qy
            pose_stamped.pose.orientation.z = qz
            pose_stamped.pose.orientation.w = qw

        ori_constraint = OrientationConstraint(
            header=pose_stamped.header,
            link_name='link6',
            orientation=pose_stamped.pose.orientation,
            weight=1.0
        )
        ori_constraint.absolute_x_axis_tolerance = 0.5
        ori_constraint.absolute_y_axis_tolerance = 0.5 # Allow some tilt in x and y (decent is e.g. 0.5)
        ori_constraint.absolute_z_axis_tolerance = 3.14 # Allow full rotation around z-axis
        constraints.orientation_constraints.append(ori_constraint)

        req.goal_constraints.append(constraints)
        plan_ops = PlanningOptions(plan_only=False)
        goal_msg = MoveGroup.Goal(request=req, planning_options=plan_ops)

        self.move_in_progress = True
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(lambda future: self.goal_accepted_callback(future))

    def goal_accepted_callback(self, future):
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().warn("Goal rejected by MoveGroup.")
                self.move_in_progress = False
                return
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(lambda future: self.goal_result_callback(future))
        except Exception as e:
            self.get_logger().error(f"Error accepting goal: {e}")
            self.move_in_progress = False

    def goal_result_callback(self, future):
        result = future.result()
        status = result.status
        if status != 4:  # 4 = SUCCEEDED
            self.get_logger().warn(f"Move failed with status: {status}")
        else:
            self.get_logger().info("MoveIt planning succeeded.")
        self.move_in_progress = False

    def compute_escape_pose(self):
        pose = PoseStamped()
        pose.header.frame_id = 'link_base'
        pose.header.stamp = self.get_clock().now().to_msg()
        x, y, z, roll, pitch, yaw = self.home_pose
        qx, qy, qz, qw = quaternion_from_euler(roll, pitch, yaw)
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def main_loop(self):
        now = time.time()
        if self.state == 'sweep':
            if not self.move_in_progress:
                self.sweep_idx = (self.sweep_idx + 1) % len(self.sweep_poses)
                x, y, z = self.sweep_poses[self.sweep_idx]
                self.get_logger().info(f"Sweeping to pose {x}, {y}, {z}")
                pose = PoseStamped()
                pose.header.frame_id = 'link_base'
                pose.header.stamp = self.get_clock().now().to_msg()
                pose.pose.position.x = x
                pose.pose.position.y = y
                pose.pose.position.z = z
                pose.pose.orientation.x = 0.0
                pose.pose.orientation.y = 0.0
                pose.pose.orientation.z = 0.0
                pose.pose.orientation.w = 0.0
                self.send_pose_goal_async(pose)
            if self.locked_target_pose and (now - self.last_detection_time < 1.0):
                self.get_logger().info("Blue square detected! Switching to servo.")
                self.state = 'servo'
                self.last_error = 999.0
                self.error_not_decreasing_count = 0.0
                self.servo_stuck_count = 0.0

                self.error_log = []
                self.time_log = []
                self.start_servo_time = time.time()

        elif self.state == 'servo':
            if not self.locked_target_pose or (now - self.last_detection_time > 10.0):
                self.get_logger().warn("Lost target or vision timeout, returning to sweep.")

                if self.error_log:
                    self.get_logger().info(
                        f"[Servo End] Final XY error: {self.error_log[-1]:.3f} m, Total time: {self.time_log[-1]:.3f} s"
                    )
                    # Optionally, store for later summary
                    self.final_errors.append(self.error_log[-1])
                    self.final_times.append(self.time_log[-1])
                    # Optionally print full logs:
                    # self.get_logger().info(f"XY Error Log: {self.error_log}")
                    # self.get_logger().info(f"Time Log: {self.time_log}")
                self.error_log = []
                self.time_log = []
                self.start_servo_time = None

                self.state = 'sweep'
                return

            try:
                trans = self.tf_buffer.lookup_transform(
                    'link_base', 'link6', rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.2)
                )
            except Exception as e:
                self.get_logger().warn(f"TF lookup failed: {e}")
                return

            # --- OPTIONAL: Transform target pose to link_base if needed ---
            if self.locked_target_pose.header.frame_id != 'link_base':
                try:
                    tf_to_base = self.tf_buffer.lookup_transform(
                        'link_base',
                        self.locked_target_pose.header.frame_id,
                        rclpy.time.Time(),
                        timeout=rclpy.duration.Duration(seconds=0.2)
                    )
                    tgt_in_base = do_transform_pose(self.locked_target_pose, tf_to_base)
                    tgt = tgt_in_base.pose.position
                except Exception as e:
                    self.get_logger().warn(f"TF for target failed: {e}")
                    return
            else:
                tgt = self.locked_target_pose.pose.position

            ee = trans.transform.translation
            dx = tgt.x - ee.x
            dy = tgt.y - ee.y
            dz = (tgt.z + self.z_offset) - ee.z
            dist = np.linalg.norm([dx, dy, dz])


            self.get_logger().info(
                f"[DEBUG] Target pose frame: {self.locked_target_pose.header.frame_id}, "
                f"EE pose frame: link_base"
            )
            self.get_logger().info(
                f"[DEBUG] Target (x, y, z): ({tgt.x:.3f}, {tgt.y:.3f}, {tgt.z:.3f}), "
                f"EE (x, y, z): ({ee.x:.3f}, {ee.y:.3f}, {ee.z:.3f}), "
                f"XY error: {np.linalg.norm([dx, dy]):.3f}, dist: {dist:.3f}"
            )

            xy_error = np.linalg.norm([dx, dy])
            elapsed_time = time.time() - self.start_servo_time if self.start_servo_time else 0.0
            self.error_log.append(xy_error)
            self.time_log.append(elapsed_time)

            # ---------- DEBUG PRINT --------------
            self.get_logger().info(f"[DEBUG] dist = {dist:.3f}, hold_distance = {self.hold_distance:.3f}")

            # Hold logic block - runs BEFORE fallback, stuck, deadzone, etc.
            if dist < self.hold_distance:
                if self.hold_start_time is None:
                    self.hold_start_time = time.time()
                    time_to_target = self.hold_start_time - self.start_servo_time if self.start_servo_time else 0.0
                    self.get_logger().info(f"Within hold_distance ({self.hold_distance:.3f} m), holding for {self.hold_duration:.1f} seconds. Time to target: {time_to_target:.1f} s")
                    self.get_logger().info("Within hold_distance, starting hold timer.")
                elif time.time() - self.hold_start_time >= self.hold_duration:
                    self.get_logger().info("Hold complete. Returning to sweep.")
                    self.state = 'sweep'
                    self.hold_start_time = None
                    return
                else:
                    # Hold position (zero velocity)
                    cmd = TwistStamped()
                    cmd.header.stamp = self.get_clock().now().to_msg()
                    cmd.header.frame_id = 'link_base'
                    cmd.twist.linear.x = 0.0
                    cmd.twist.linear.y = 0.0
                    cmd.twist.linear.z = 0.0
                    cmd.twist.angular.x = 0.0
                    cmd.twist.angular.y = 0.0
                    cmd.twist.angular.z = 0.0
                    self.cmd_pub.publish(cmd)
                    return
            elif dist > self.hold_distance + self.hold_margin:
                self.hold_start_time = None

            # --- PATCH: Detect fallback (Z == 0.3 means fallback) ---
            fallback_z = 0.3
            using_fallback = abs(tgt.z - fallback_z) < 1e-3

            # --- PATCH: Optionally slow down when using fallback ---
            if using_fallback:
                max_v = self.max_speed * 0.2  # Slow speed in blind mode
                self.get_logger().warn("Using 2D fallback pose, going in blind!")
            else:
                if dist < 0.18:
                    max_v = self.max_speed * 0.5
                else:
                    max_v = self.max_speed

            # --- PATCH: Only do stuck detection if NOT using fallback ---
            if not using_fallback:
                if abs(self.last_error - dist) < 0.003:
                    self.error_not_decreasing_count += 1.0
                else:
                    self.error_not_decreasing_count = 0.0
                self.last_error = dist

                if self.error_not_decreasing_count > 10.0:
                    self.servo_stuck_count += 1.0
                    self.get_logger().warn("Servo appears stuck (not progressing toward target).")
                else:
                    self.servo_stuck_count = 0.0

                if self.servo_stuck_count > 3:
                    self.get_logger().warn("Servo stuck or singularity/joint limit detected. Switching to ESCAPE.")
                    self.state = 'escape'
                    self.escape_pose = self.compute_escape_pose()
                    self.servo_stuck_count = 0.0
                    return
            else:
                self.error_not_decreasing_count = 0.0
                self.servo_stuck_count = 0.0

            # --- PATCH: Deadzone to avoid jitter ---
            if dist < self.deadzone:
                vx = vy = vz = 0.0
                self.get_logger().info("Within deadzone, not moving to prevent jitter.")
                cmd = TwistStamped()
                cmd.header.stamp = self.get_clock().now().to_msg()
                cmd.header.frame_id = 'link_base'
                cmd.twist.linear.x = vx
                cmd.twist.linear.y = vy
                cmd.twist.linear.z = vz
                cmd.twist.angular.x = 0.0
                cmd.twist.angular.y = 0.0
                cmd.twist.angular.z = 0.0
                self.cmd_pub.publish(cmd)
                return

            # --- PATCH: Only switch to plan if NOT using fallback ---
            if dist < self.servo_to_plan_thresh and (now - self.last_servo_to_plan_time > 1.0) and not using_fallback:
                self.get_logger().info("Within 10cm, switching to MoveIt planning for final approach.")
                self.state = 'plan'
                self.last_servo_to_plan_time = now
                return

            if self.servo_stuck_count > 3:
                self.get_logger().warn("Servo stuck or singularity/joint limit detected. Switching to ESCAPE.")
                self.state = 'escape'
                self.escape_pose = self.compute_escape_pose()
                self.servo_stuck_count = 0.0
                return

            vx = np.clip(self.kp * dx, -max_v, max_v)
            vy = np.clip(self.kp * dy, -max_v, max_v)
            vz = np.clip(self.kp * dz, -max_v, max_v)

            cmd = TwistStamped()
            cmd.header.stamp = self.get_clock().now().to_msg()
            cmd.header.frame_id = 'link_base'
            cmd.twist.linear.x = vx
            cmd.twist.linear.y = vy
            cmd.twist.linear.z = vz

            # --- Look-at angular velocity control ---
            try:
                q = trans.transform.rotation
                quat = [q.x, q.y, q.z, q.w]
                rot_matrix = quaternion_matrix(quat)
                current_z = rot_matrix[:3, 2]  # EE Z axis in base frame
            except Exception as e:
                self.get_logger().warn(f"TF orientation failed: {e}")
                current_z = np.array([0.0, 0.0, 1.0])

            vec = np.array([dx, dy, dz])
            vec_norm = np.linalg.norm(vec)
            if vec_norm > 1e-6:
                vec = vec / vec_norm
            else:
                vec = np.array([0.0, 0.0, 1.0])

            axis = np.cross(current_z, vec)
            axis_norm = np.linalg.norm(axis)
            angle = np.arccos(np.clip(np.dot(current_z, vec), -1.0, 1.0))

            if axis_norm > 1e-6:
                axis = axis / axis_norm
                angular_vel = 0.8 * angle * axis  # Gain can be tuned
            else:
                angular_vel = np.zeros(3)

            cmd.twist.angular.x = float(angular_vel[0])
            cmd.twist.angular.y = float(angular_vel[1])
            cmd.twist.angular.z = float(angular_vel[2])

            self.cmd_pub.publish(cmd)
            self.get_logger().info(
                f"PBVS cmd: [{vx:.3f}, {vy:.3f}, {vz:.3f}] | ang: [{angular_vel[0]:.3f}, {angular_vel[1]:.3f}, {angular_vel[2]:.3f}] | err = {dist:.3f} m"
            )

        elif self.state == 'plan':
            if not self.move_in_progress:
                self.get_logger().info("Planning and executing final approach with MoveIt...")
                if self.locked_target_pose:
                    final_pose = deepcopy(self.locked_target_pose)
                    final_pose.header.stamp = self.get_clock().now().to_msg()
                    final_pose.pose.position.z += self.z_offset + self.servo_to_plan_thresh
                    qx, qy, qz, qw = quaternion_from_euler(self.approach_tilt_rad, 0, np.pi)
                    final_pose.pose.orientation.x = qx
                    final_pose.pose.orientation.y = qy
                    final_pose.pose.orientation.z = qz
                    final_pose.pose.orientation.w = qw
                    self.send_pose_goal_async(final_pose)
                self.state = 'wait_for_plan'

        elif self.state == 'wait_for_plan':
            if not self.move_in_progress:
                self.get_logger().info("Final approach complete. Resuming sweep.")
                self.locked_target_pose = None
                self.filtered_target_pose = None
                self.state = 'sweep'

        elif self.state == 'escape':
            if not self.move_in_progress:
                self.get_logger().warn("Planning escape to home pose due to singularity/joint limit.")
                self.send_pose_goal_async(self.escape_pose)
                self.state = 'wait_for_escape'

        elif self.state == 'wait_for_escape':
            if not self.move_in_progress:
                self.get_logger().info("Escape move complete. Returning to sweep mode.")
                self.locked_target_pose = None
                self.filtered_target_pose = None
                self.state = 'sweep'

def main(args=None):
    rclpy.init(args=args)
    node = HybridServoPlan()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

