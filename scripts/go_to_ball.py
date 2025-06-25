import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, WorkspaceParameters
from shape_msgs.msg import SolidPrimitive
from rclpy.action import ActionClient
import time
import numpy as np
import tf_transformations  # Make sure python3-tf-transformations is installed

class MoveItPoseGoalClient(Node):
    def __init__(self):
        super().__init__('moveit_pose_goal_client')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/red_ball_pose', self.pose_cb, 10)
        self.last_pose = None
        self.last_goal_time = 0

    def pose_cb(self, msg):
        # Only send a new goal every 3 seconds
        now = time.time()
        if now - self.last_goal_time < 3.0:
            return

        # Stop 1cm above the detected ball (change this value as needed)
        adjusted_pose = PoseStamped()
        adjusted_pose.header = msg.header
        adjusted_pose.pose.position.x = msg.pose.position.x
        adjusted_pose.pose.position.y = msg.pose.position.y
        adjusted_pose.pose.position.z = msg.pose.position.z + 0.25  # 25cm above

        # Set orientation to z-down (180deg about x-axis)
        quat = tf_transformations.quaternion_from_euler(np.pi, 0, 0)  # (roll, pitch, yaw)
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
        self.get_logger().info(f"Sending new pose goal to MoveIt (1cm above red ball, z-down)!")
        self.send_pose_goal(adjusted_pose)

    def send_pose_goal(self, pose):
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            return

        # Build a MotionPlanRequest
        req = MotionPlanRequest()
        req.group_name = 'xarm6'
        req.goal_constraints.append(Constraints())
        req.goal_constraints[0].position_constraints.append(PositionConstraint())
        req.goal_constraints[0].position_constraints[0].header = pose.header
        req.goal_constraints[0].position_constraints[0].link_name = 'link6'
        req.goal_constraints[0].position_constraints[0].constraint_region.primitives.append(
            SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.02]))  # 2cm radius for easier planning
        req.goal_constraints[0].position_constraints[0].constraint_region.primitive_poses.append(pose.pose)
        req.goal_constraints[0].position_constraints[0].weight = 1.0

        # Add orientation constraint to keep end-effector pointing down
        ori_constraint = OrientationConstraint()
        ori_constraint.header = pose.header
        ori_constraint.link_name = 'link6'
        ori_constraint.orientation = pose.pose.orientation
        ori_constraint.absolute_x_axis_tolerance = 0.2  # Looser tolerance for easier planning
        ori_constraint.absolute_y_axis_tolerance = 0.2
        ori_constraint.absolute_z_axis_tolerance = 3.14  # Allow free rotation around z
        ori_constraint.weight = 1.0
        req.goal_constraints[0].orientation_constraints.append(ori_constraint)

        # Workspace (optional, can be left default)
        req.workspace_parameters = WorkspaceParameters()

        # Build the MoveGroup goal
        goal_msg = MoveGroup.Goal()
        goal_msg.request = req
        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.look_around = False
        goal_msg.planning_options.replan = False

        # Send the goal
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