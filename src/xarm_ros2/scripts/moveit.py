import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, WorkspaceParameters
from shape_msgs.msg import SolidPrimitive
from rclpy.action import ActionClient

class MoveItPoseGoalClient(Node):
    def __init__(self):
        super().__init__('moveit_pose_goal_client')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.create_subscription(PoseStamped, '/blue_square_pose', self.pose_cb, 10)
        self.last_pose = None

    def pose_cb(self, msg):
        if self.last_pose is not None:
            dist = ((msg.pose.position.x - self.last_pose.pose.position.x) ** 2 +
                    (msg.pose.position.y - self.last_pose.pose.position.y) ** 2 +
                    (msg.pose.position.z - self.last_pose.pose.position.z) ** 2) ** 0.5
            if dist < 0.01:
                return
        self.last_pose = msg
        self.get_logger().info(f"Sending new pose goal to MoveIt!")
        self.send_pose_goal(msg)

    def send_pose_goal(self, pose):
        # Wait for the action server to be available
        if not self._action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("MoveGroup action server not available!")
            return

        # Build a MotionPlanRequest
        req = MotionPlanRequest()
        req.group_name = 'xarm6'
        req.goal_constraints.append(Constraints())
        req.goal_constraints[0].position_constraints.append(PositionConstraint())
        req.goal_constraints[0].position_constraints[0].header = pose.header
        req.goal_constraints[0].position_constraints[0].link_name = 'link6'  # or your camera link
        req.goal_constraints[0].position_constraints[0].constraint_region.primitives.append(SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.01]))
        req.goal_constraints[0].position_constraints[0].constraint_region.primitive_poses.append(pose.pose)
        req.goal_constraints[0].position_constraints[0].weight = 1.0

        # Optionally add orientation constraint if you want the camera to "look at" the cube
        # req.goal_constraints[0].orientation_constraints.append(OrientationConstraint(...))

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