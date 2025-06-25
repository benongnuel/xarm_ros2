#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Pose
from rclpy.action import ActionClient
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, PositionConstraint, OrientationConstraint, BoundingVolume, CollisionObject
from shape_msgs.msg import SolidPrimitive
import numpy as np
import time

class RasterScan(Node):
    def __init__(self):
        super().__init__('raster_scan')
        self.moveit_client = ActionClient(self, MoveGroup, "/move_action")
        self.scan_area_x = (-0.4, 0.4)
        self.scan_area_y = (-0.15, 0.15)
        self.z_height = 0  # Raise this if your table is higher!
        self.min_z_height = 0.5  # Never go below this height (adjust for your table)
        self.num_x = 10
        self.num_y = 5
        self.sleep_time = 4.0

        # Store latest blue square pose and timestamp
        self.blue_square_pose = None
        self.blue_square_stamp = 0.0
        self.blue_square_detected = False
        self.current_goal_handle = None
        self.current_pose = None
        self.create_subscription(PoseStamped, '/blue_square_pose', self.blue_square_callback, 10)
        self.planning_scene_pub = self.create_publisher(CollisionObject, '/collision_object', 10)
        self.add_floor_to_scene()

    def blue_square_callback(self, msg):
        self.blue_square_pose = msg
        self.blue_square_stamp = time.time()
        # Only stop if close and facing (z difference small)
        if self.current_pose is not None:
            ee = np.array([
                self.current_pose.pose.position.x,
                self.current_pose.pose.position.y,
                self.current_pose.pose.position.z
            ])
            sq = np.array([
                msg.pose.position.x,
                msg.pose.position.y,
                msg.pose.position.z
            ])
            dist = np.linalg.norm(ee - sq)
        if dist < 1.75:
            self.blue_square_detected = True
            self.get_logger().info(f"Blue square detected at {dist:.2f}m! Stopping scan.")
            if self.current_goal_handle is not None:
                self.get_logger().info("Cancelling current MoveIt goal.")
                self.current_goal_handle.cancel_goal_async()
        else:
            self.get_logger().info(f"Blue square detected at {dist:.2f}m but not close enough, continuing.")

    def add_floor_to_scene(self):
        from moveit_msgs.msg import CollisionObject
        from shape_msgs.msg import SolidPrimitive
        from geometry_msgs.msg import Pose

        floor = CollisionObject()
        floor.header.frame_id = "world"
        floor.id = "floor"
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [5.0, 5.0, 0.01]  # 5x5 meters, 1cm thick
        floor.primitives = [primitive]
        floor_pose = Pose()
        floor_pose.position.x = 0.0
        floor_pose.position.y = 0.0
        floor_pose.position.z = -0.005  # So top of floor is at z=0
        floor_pose.orientation.w = 1.0
        floor.primitive_poses = [floor_pose]
        floor.operation = CollisionObject.ADD

        self.planning_scene_pub = self.create_publisher(CollisionObject, '/collision_object', 10)
        time.sleep(1)
        self.planning_scene_pub.publish(floor)
        self.get_logger().info("Floor added to MoveIt planning scene.")
        
    def orientation_quat(self):
        quat = [0.0, 0.0, 0.0, 1.0]
        return quat

    def make_pose(self, x, y):
        pose = PoseStamped()
        pose.header.frame_id = "world"
        pose.pose.position.x = x
        pose.pose.position.y = y
        # Safety: never go below min_z_height
        pose.pose.position.z = max(self.z_height, self.min_z_height)
        quat = self.orientation_quat()
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]
        return pose

    def _pose_constraint(self, pose_msg):
        pos_constraint = PositionConstraint()
        pos_constraint.header = pose_msg.header
        pos_constraint.link_name = "link_eef"
        bv = BoundingVolume()
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        bv.primitives = [primitive]
        bv.primitive_poses = [pose_msg.pose]
        pos_constraint.constraint_region = bv
        pos_constraint.weight = 1.0

        orient_constraint = OrientationConstraint()
        orient_constraint.header = pose_msg.header
        orient_constraint.link_name = "link_eef"
        orient_constraint.orientation = pose_msg.pose.orientation
        orient_constraint.absolute_x_axis_tolerance = 0.1
        orient_constraint.absolute_y_axis_tolerance = 0.1
        orient_constraint.absolute_z_axis_tolerance = 3.14
        orient_constraint.weight = 1.0

        c = Constraints()
        c.position_constraints = [pos_constraint]
        c.orientation_constraints = [orient_constraint]
        return c

    def _goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by MoveIt!")
            self.current_goal_handle = None
            return
        self.get_logger().info("Goal accepted. Waiting for result...")
        self.current_goal_handle = goal_handle
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self._get_result_callback)

    def _get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info(f"MoveIt result: {result.error_code.val}")
        self.current_goal_handle = None

    def go_to_pose(self, pose_stamped):
        self.current_pose = pose_stamped  # Store for distance/facing check
        if self.blue_square_detected:
            self.get_logger().info("Scan interrupted due to blue square detection.")
            return
        goal_msg = MoveGroup.Goal()
        goal_msg.request.group_name = "xarm6"
        goal_msg.request.goal_constraints = [self._pose_constraint(pose_stamped)]
        goal_msg.request.max_velocity_scaling_factor = 0.05
        goal_msg.request.max_acceleration_scaling_factor = 0.05
        self.moveit_client.wait_for_server()
        self.get_logger().info(
            f"Sending MoveGroup goal: x={pose_stamped.pose.position.x:.3f}, "
            f"y={pose_stamped.pose.position.y:.3f}, z={pose_stamped.pose.position.z:.3f}"
        )
        send_goal_future = self.moveit_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self._goal_response_callback)

        sleep_time = self.sleep_time
        interval = 0.1
        waited = 0.0
        while waited < sleep_time:
            if self.blue_square_detected:
                self.get_logger().info("Scan interrupted during wait due to blue square detection.")
                return
            rclpy.spin_once(self, timeout_sec=interval)
            time.sleep(interval)
            waited += interval

    def raster_scan(self):
        xs = np.linspace(self.scan_area_x[0], self.scan_area_x[1], self.num_x)
        ys = np.linspace(self.scan_area_y[0], self.scan_area_y[1], self.num_y)
        go_right = True
        for yi, y in enumerate(ys):
            row_xs = xs if go_right else xs[::-1]
            go_right = not go_right
            for x in row_xs:
                if self.blue_square_detected:
                    self.get_logger().info("Raster scan stopped due to blue square detection.")
                    return
                pose = self.make_pose(x, y)
                self.go_to_pose(pose)
        self.get_logger().info("Raster scan complete.")

def main(args=None):
    rclpy.init(args=args)
    node = RasterScan()
    node.raster_scan()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()