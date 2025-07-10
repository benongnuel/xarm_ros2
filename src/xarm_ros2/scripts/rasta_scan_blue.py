#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import MotionPlanRequest, Constraints, PositionConstraint, OrientationConstraint, PlanningOptions
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import PoseStamped
from tf_transformations import quaternion_from_euler
import numpy as np

class FixedPoseTest(Node):
    def __init__(self):
        super().__init__('fixed_pose_test')
        self._action_client = ActionClient(self, MoveGroup, 'move_action')
        self.timer = self.create_timer(2.0, self.send_goal)

    def send_goal(self):
        # Define your target pose here
        target = PoseStamped()
        target.header.frame_id = 'link_base'
        target.pose.position.x = 0.30
        target.pose.position.y = 0.000
        target.pose.position.z = 0.70
        qx, qy, qz, qw = quaternion_from_euler(np.pi, 0.0, 0.0)
        target.pose.orientation.x = qx
        target.pose.orientation.y = qy
        target.pose.orientation.z = qz
        target.pose.orientation.w = qw

        req = MotionPlanRequest(group_name='xarm6', allowed_planning_time=3.0, num_planning_attempts=5)
        constraints = Constraints()
        pos_constraint = PositionConstraint(header=target.header, link_name='link_eef', weight=1.0)
        pos_constraint.constraint_region.primitives.append(SolidPrimitive(type=SolidPrimitive.SPHERE, dimensions=[0.015]))
        pos_constraint.constraint_region.primitive_poses.append(target.pose)
        constraints.position_constraints.append(pos_constraint)

        req.goal_constraints.append(constraints)
        plan_ops = PlanningOptions(plan_only=False)
        goal_msg = MoveGroup.Goal(request=req, planning_options=plan_ops)

        # Send MoveIt goal
        self.get_logger().info("Sending fixed pose goal to MoveIt...")
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_accepted_callback)
        self.timer.cancel()

    def goal_accepted_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn("Goal rejected by MoveGroup.")
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.goal_result_callback)

    def goal_result_callback(self, future):
        result = future.result()
        status = result.status
        if status == 4:  # 4 = SUCCEEDED
            self.get_logger().info("MoveIt planning SUCCEEDED.")
        else:
            self.get_logger().warn(f"MoveIt planning failed with status: {status}")

def main(args=None):
    rclpy.init(args=args)
    node = FixedPoseTest()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
