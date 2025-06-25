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

class MoveItPoseGoalClient(Node):
    def __init__(self):
        super().__init__('moveit_pose_goal_client')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/red_ball_pose', self.pose_cb, 10)
        self.last_pose = None
        self.last_goal_time = 0
        self.found_ball = False
        self.sweep_idx = 0
        self.sweep_waypoints = [
            # Define sweeping waypoints (x, y, z)
            (-0.45, -0.45, 0.45),
            (-0.45,  0.45, 0.45),
            ( 0.45,  0.45, 0.45),
            ( 0.45, -0.45, 0.45),
        ]
        self.timer = self.create_timer(4.0, self.sweep_motion)  # Sweep every 4 seconds

        # For cooldown after visiting a ball
        self.ignore_until = 0
        self.last_ball_position = None
        self.reset_timer = None
        self.last_ball_pose = None

    def pose_cb(self, msg):
        now = time.time()
        # Ignore ball detections during cooldown
        if now < self.ignore_until:
            return

        # Ignore if ball is at (almost) the same position as last visited
        if self.last_ball_position is not None:
            dx = msg.pose.position.x - self.last_ball_position[0]
            dy = msg.pose.position.y - self.last_ball_position[1]
            dz = msg.pose.position.z - self.last_ball_position[2]
            if (dx**2 + dy**2 + dz**2) < 0.0025:  # 5cm squared
                return

        self.found_ball = True
        self.last_ball_pose = msg  # Save the last ball pose

        if now - self.last_goal_time < 3.0:
            return

        adjusted_pose = PoseStamped()
        adjusted_pose.header = msg.header
        adjusted_pose.pose.position.x = msg.pose.position.x
        adjusted_pose.pose.position.y = msg.pose.position.y
        adjusted_pose.pose.position.z = msg.pose.position.z + 0.25  # 25cm above

        quat = tf_transformations.quaternion_from_euler(np.pi, 0, 0)
        adjusted_pose.pose.orientation.x = quat[0]
        adjusted_pose.pose.orientation.y = quat[1]
        adjusted_pose.pose.orientation.z = quat[2]
        adjusted_pose.pose.orientation.w = quat[3]

        if self.last_pose is not None:
            dist = ((adjusted_pose.pose.position.x - self.last_pose.pose.position.x) ** 2 +
                    (adjusted_pose.pose.position.y - self.last_pose.pose.position.y) ** 2 +
                    (adjusted_pose.pose.position.z - self.last_pose.pose.position.z) ** 2) ** 0.5
            if dist < 0.01:
                return
        self.last_pose = adjusted_pose
        self.last_goal_time = now
        self.get_logger().info("Red ball found! Moving to it.")
        self.send_pose_goal(adjusted_pose)

        # Start/reset the timer to move up and resume sweeping after 5 seconds
        if self.reset_timer is not None:
            self.reset_timer.cancel()
        self.reset_timer = self.create_timer(5.0, self.move_up_and_reset)

        # Save last ball position for ignore logic
        self.last_ball_position = (
            msg.pose.position.x,
            msg.pose.position.y,
            msg.pose.position.z
        )

    def move_up_and_reset(self):
        # Move up from the last ball position
        if self.last_ball_pose is None:
            return
        up_pose = PoseStamped()
        up_pose.header = self.last_ball_pose.header
        up_pose.pose.position.x = self.last_ball_pose.pose.position.x
        up_pose.pose.position.y = self.last_ball_pose.pose.position.y
        up_pose.pose.position.z = self.last_ball_pose.pose.position.z + 0.35  # Move up 35cm from ball

        quat = tf_transformations.quaternion_from_euler(np.pi, 0, 0)
        up_pose.pose.orientation.x = quat[0]
        up_pose.pose.orientation.y = quat[1]
        up_pose.pose.orientation.z = quat[2]
        up_pose.pose.orientation.w = quat[3]

        self.get_logger().info("Moving up to scan for another ball.")
        self.send_pose_goal(up_pose)

        # Reset for next search
        self.found_ball = False
        self.last_ball_pose = None

        # Ignore the same ball for 5 seconds
        self.ignore_until = time.time() + 3.0

        # Cancel this timer so it doesn't repeat
        if self.reset_timer is not None:
            self.reset_timer.cancel()
            self.reset_timer = None

    def sweep_motion(self):
        if self.found_ball:
            return  # Stop sweeping if ball is found

        # Send next sweep waypoint
        x, y, z = self.sweep_waypoints[self.sweep_idx]
        sweep_pose = PoseStamped()
        sweep_pose.header.frame_id = 'link_base'  # Or your robot's base frame
        sweep_pose.pose.position.x = x
        sweep_pose.pose.position.y = y
        sweep_pose.pose.position.z = z

        quat = tf_transformations.quaternion_from_euler(np.pi, 0, 0)
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
            SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.02]))
        req.goal_constraints[0].position_constraints[0].constraint_region.primitive_poses.append(pose.pose)
        req.goal_constraints[0].position_constraints[0].weight = 1.0

        ori_constraint = OrientationConstraint()
        ori_constraint.header = pose.header
        ori_constraint.link_name = 'link6'
        ori_constraint.orientation = pose.pose.orientation
        ori_constraint.absolute_x_axis_tolerance = 0.2
        ori_constraint.absolute_y_axis_tolerance = 0.2
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
    node = MoveItPoseGoalClient()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()