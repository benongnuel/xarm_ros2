#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, PositionConstraint, BoundingVolume, JointConstraint
from shape_msgs.msg import SolidPrimitive
import numpy as np
import tf2_ros
import time

class VisualServoMoveIt(Node):
    def __init__(self):
        super().__init__('visual_servo_moveit')

        # Action client for MoveIt
        self.moveit_client = ActionClient(self, MoveGroup, "/move_action")

        # Subscribe to blue square pose
        self.create_subscription(PoseStamped, '/blue_square_pose', self.blue_square_callback, 10)

        # TF2 buffer and listener for EE pose
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Servo gains (tune for speed/stability)
        self.Kp = 0.01
        self.Kd = 0.001

        self.prev_time = self.get_clock().now()
        self.prev_pose = None

        self.target_pose = None
        self.visual_servo_active = False

        # Move to initial joint pose first
        self.move_to_initial_pose()

        # Start servo timer (but it will only run after initial pose is reached)
        self.timer = self.create_timer(0.2, self.servo_step)

    def move_to_initial_pose(self):
        # Set your initial joint values (in radians)
        joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        # This pose should let the camera see the blue square
        joint_values_deg = [23, 44, -84, -166, 140, -28]
        joint_values = [np.deg2rad(j) for j in joint_values_deg]

        constraints = Constraints()
        for name, value in zip(joint_names, joint_values):
            jc = JointConstraint()
            jc.joint_name = name
            jc.position = value
            jc.tolerance_above = 0.01
            jc.tolerance_below = 0.01
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)

        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = "xarm6"
        goal_msg.request.goal_constraints = [constraints]
        goal_msg.request.max_velocity_scaling_factor = 0.2
        goal_msg.request.max_acceleration_scaling_factor = 0.2

        self.moveit_client.wait_for_server()
        future = self.moveit_client.send_goal_async(goal_msg)
        future.add_done_callback(self.initial_pose_done)
        

    def initial_pose_done(self, future):
        self.get_logger().info("Initial joint pose reached. Visual servoing will start.")
        self.visual_servo_active = True

    def blue_square_callback(self, msg):
        self.target_pose = msg

    def get_current_ee_pose(self):
        try:
            trans = self.tf_buffer.lookup_transform(
                'world', 'link_eef', rclpy.time.Time())
            pose = PoseStamped()
            pose.header = trans.header
            pose.pose.position.x = trans.transform.translation.x
            pose.pose.position.y = trans.transform.translation.y
            pose.pose.position.z = trans.transform.translation.z
            pose.pose.orientation = trans.transform.rotation
            return pose
        except Exception as e:
            self.get_logger().warn(f"TF lookup failed: {e}")
            return None

    def servo_step(self):
        if not self.visual_servo_active:
            return

        if self.target_pose is None:
            return

        current_pose = self.get_current_ee_pose()
        if current_pose is None:
            return

        now = self.get_clock().now()
        dt = (now - self.prev_time).nanoseconds * 1e-9 if self.prev_pose else 0.2

        # Compute error (XYZ)
        error = np.array([
            self.target_pose.pose.position.x - current_pose.pose.position.x,
            self.target_pose.pose.position.y - current_pose.pose.position.y,
            self.target_pose.pose.position.z - current_pose.pose.position.z
        ])

        # Stop if close enough (2cm)
        if np.linalg.norm(error) < 0.02:
            self.get_logger().info("Target reached. Stopping servo.")
            return

        # Derivative (velocity)
        if self.prev_pose:
            dpos = np.array([
                current_pose.pose.position.x - self.prev_pose.pose.position.x,
                current_pose.pose.position.y - self.prev_pose.pose.position.y,
                current_pose.pose.position.z - self.prev_pose.pose.position.z
            ])
            dpos_dt = dpos / dt
        else:
            dpos_dt = np.zeros(3)

        # PD Control
        step = self.Kp * error - self.Kd * dpos_dt

        # Limit max step size for safety (meters per cycle)
        max_step = 0.05  # 5 cm per cycle
        if np.linalg.norm(step) > max_step:
            step = step * (max_step / np.linalg.norm(step))

        # Update pose for MoveIt goal
        new_pose = PoseStamped()
        new_pose.header.frame_id = 'world'
        new_pose.pose.position.x = current_pose.pose.position.x + step[0]
        new_pose.pose.position.y = current_pose.pose.position.y + step[1]
        new_pose.pose.position.z = current_pose.pose.position.z + step[2]
        new_pose.pose.orientation = current_pose.pose.orientation

        # Send new pose as MoveIt goal
        self.go_to_pose(new_pose)

        self.get_logger().info(
            f"Step: error={error}, step={step}, pose=({new_pose.pose.position.x:.3f}, {new_pose.pose.position.y:.3f}, {new_pose.pose.position.z:.3f})"
        )

        self.prev_pose = current_pose
        self.prev_time = now

    def go_to_pose(self, pose_stamped):
        pos_constraint = PositionConstraint()
        pos_constraint.header = pose_stamped.header
        pos_constraint.link_name = "link_eef"
        bv = BoundingVolume()
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [0.05, 0.05, 0.05]  # 5cm box for easier planning
        bv.primitives = [primitive]
        bv.primitive_poses = [pose_stamped.pose]
        pos_constraint.constraint_region = bv
        pos_constraint.weight = 1.0

        from moveit_msgs.msg import Constraints
        constraints = Constraints()
        constraints.position_constraints = [pos_constraint]

        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = "xarm6"
        goal_msg.request.goal_constraints = [constraints]
        goal_msg.request.max_velocity_scaling_factor = 0.2
        goal_msg.request.max_acceleration_scaling_factor = 0.2

        self.moveit_client.wait_for_server()
        send_goal_future = self.moveit_client.send_goal_async(goal_msg)

def main(args=None):
    rclpy.init(args=args)
    node = VisualServoMoveIt()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()