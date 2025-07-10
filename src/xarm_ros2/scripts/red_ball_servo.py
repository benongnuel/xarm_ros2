#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TwistStamped
import numpy as np
import tf2_ros
import time
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, PlanningOptions
from shape_msgs.msg import SolidPrimitive
from tf_transformations import quaternion_from_euler

class RedBallServoPBVS(Node):
    def __init__(self):
        super().__init__('red_ball_servo_pbvs')
        self.state = 'sweep'
        self.sweep_poses = [
            ( 0.3, -0.3, 0.5), ( 0.3,  0.3, 0.5),
            (-0.3,  0.3, 0.5), (-0.3, -0.3, 0.5),
        ]
        self.sweep_idx = 0
        self.sweep_in_progress = False
        self.target_pose = None
        self.last_detection_time = time.time()

        self.sub = self.create_subscription(PoseStamped, '/red_ball_pose', self.cb, 1)
        self.pub = self.create_publisher(TwistStamped, '/servo_server/delta_twist_cmds', 10)
        self.timer = self.create_timer(0.1, self.main_loop)  # 10 Hz

        self.Kp = 0.5
        self.stop_threshold = 0.05
        self.max_vel = 0.1
        self.fixed_z = 0.03

        # TF buffer/listener for EE pose feedback
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # MoveIt action client
        self._action_client = ActionClient(self, MoveGroup, 'move_action')

    def cb(self, msg):
        self.target_pose = msg
        self.last_detection_time = time.time()

    def send_pose_goal_async(self, pose_stamped):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            return

        req = MotionPlanRequest(group_name='xarm6', allowed_planning_time=3.0, num_planning_attempts=5)
        pose_stamped.header.stamp = self.get_clock().now().to_msg()

        constraints = Constraints()
        pos_constraint = PositionConstraint(header=pose_stamped.header, link_name='link_eef', weight=1.0)
        pos_constraint.constraint_region.primitives.append(SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.015]))
        pos_constraint.constraint_region.primitive_poses.append(pose_stamped.pose)
        constraints.position_constraints.append(pos_constraint)

        ori_constraint = OrientationConstraint(header=pose_stamped.header, link_name='link_eef', orientation=pose_stamped.pose.orientation, weight=1.0)
        ori_constraint.absolute_x_axis_tolerance = 0.1
        ori_constraint.absolute_y_axis_tolerance = 0.1
        ori_constraint.absolute_z_axis_tolerance = 3.14
        constraints.orientation_constraints.append(ori_constraint)

        req.goal_constraints.append(constraints)
        plan_ops = PlanningOptions(plan_only=False)
        goal_msg = MoveGroup.Goal(request=req, planning_options=plan_ops)

        self.sweep_in_progress = True
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(lambda future: self.goal_accepted_callback(future))

    def goal_accepted_callback(self, future):
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().warn("Goal rejected by MoveGroup.")
                self.sweep_in_progress = False
                return
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(lambda future: self.goal_result_callback(future))
        except Exception as e:
            self.get_logger().error(f"Error accepting goal: {e}")
            self.sweep_in_progress = False

    def goal_result_callback(self, future):
        result = future.result()
        status = result.status
        if status != 4:  # 4 = SUCCEEDED
            self.get_logger().warn(f"Move failed with status: {status}")
        else:
            self.get_logger().info("MoveIt planning succeeded.")
        self.sweep_in_progress = False

    def main_loop(self):
        if self.state == 'sweep':
            # Move to next sweep pose if not already moving
            if not self.sweep_in_progress:
                self.sweep_idx = (self.sweep_idx + 1) % len(self.sweep_poses)
                x, y, z = self.sweep_poses[self.sweep_idx]
                self.get_logger().info(f"Sweeping to pose {x}, {y}, {z}")
                # ...existing code...

                pose = PoseStamped()
                pose.header.frame_id = 'link_base'
                pose.header.stamp = self.get_clock().now().to_msg()
                pose.pose.position.x = x
                pose.pose.position.y = y
                pose.pose.position.z = z
                qx, qy, qz, qw = quaternion_from_euler(np.pi, 0, 0)  # EEF z-axis down
                pose.pose.orientation.x = qx
                pose.pose.orientation.y = qy
                pose.pose.orientation.z = qz
                pose.pose.orientation.w = qw
                self.send_pose_goal_async(pose)

            # If target detected, switch to servo
            if self.target_pose and (time.time() - self.last_detection_time < 1.0):
                self.get_logger().info("Red ball detected! Switching to servo.")
                self.state = 'servo'

        elif self.state == 'servo':
            if not self.target_pose:
                self.get_logger().warn("Lost target, returning to sweep.")
                self.state = 'sweep'
                return

            # Get current EE pose from TF
            try:
                tf = self.tf_buffer.lookup_transform(
                    "link_base", "link_eef", rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.2)
                )
                ee_x = tf.transform.translation.x
                ee_y = tf.transform.translation.y
                ee_z = tf.transform.translation.z
            except Exception as e:
                self.get_logger().warn(f"TF lookup failed: {e}")
                return

            # Target position (goal)
            tx = self.target_pose.pose.position.x
            ty = self.target_pose.pose.position.y
            tz = self.target_pose.pose.position.z + self.fixed_z  # Hover above ball

            # Compute error from current EE pose
            dx = tx - ee_x
            dy = ty - ee_y
            dz = tz - ee_z

            error = np.linalg.norm([dx, dy, dz])
            if error < self.stop_threshold:
                self.get_logger().info(f"Red ball reached (err={error:.3f}m), stopping servo and resuming sweep.")
                self.get_logger().info(
                    f"Final EE pose: x={ee_x:.3f}, y={ee_y:.3f}, z={ee_z:.3f}"
                )
                self.get_logger().info(
                    f"Target pose: x={tx:.3f}, y={ty:.3f}, z={tz:.3f}"
                )
                self.state = 'sweep'
                self.target_pose = None  # Clear target so it waits for a new one
                return  # Stop moving

            # Proportional velocity control (saturate to max_vel)
            vx = np.clip(self.Kp * dx, -self.max_vel, self.max_vel)
            vy = np.clip(self.Kp * dy, -self.max_vel, self.max_vel)
            vz = np.clip(self.Kp * dz, -self.max_vel, self.max_vel)

            twist = TwistStamped()
            twist.header.stamp = self.get_clock().now().to_msg()
            twist.header.frame_id = "link_base"
            twist.twist.linear.x = vx
            twist.twist.linear.y = vy
            twist.twist.linear.z = vz
            twist.twist.angular.x = 0.0
            twist.twist.angular.y = 0.0
            twist.twist.angular.z = 0.0

            self.pub.publish(twist)
            self.get_logger().info(
                f"PBVS cmd: [{vx:.3f}, {vy:.3f}, {vz:.3f}] | err = {error:.3f} m"
            )

def main(args=None):
    rclpy.init(args=args)
    node = RedBallServoPBVS()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()