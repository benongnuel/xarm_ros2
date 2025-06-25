#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetEntityState
from geometry_msgs.msg import Pose, Point, Quaternion

class SquareMover(Node):
    def __init__(self):
        super().__init__('square_mover_client')
        self.cli = self.create_client(SetEntityState, '/gazebo/set_entity_state')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Gazebo "set_entity_state" service not available, waiting...')
        self.req = SetEntityState.Request()

    def move_square(self, x, y, z):
        self.req.state.name = 'blue_square'
        self.req.state.pose.position = Point(x=x, y=y, z=z)
        self.req.state.pose.orientation = Quaternion(x=0.0, y=0.0, z=0.0, w=1.0)
        self.req.state.reference_frame = 'world'
        
        future = self.cli.call_async(self.req)
        rclpy.spin_until_future_complete(self, future)
        
        if future.result() is not None and future.result().success:
            self.get_logger().info(f"Successfully moved blue_square to ({x}, {y}, {z})")
        else:
            self.get_logger().error("Failed to move blue_square.")

def main(args=None):
    rclpy.init(args=args)
    mover_client = SquareMover()
    
    # --- DEFINE THE NEW POSITION FOR THE SQUARE HERE ---
    new_x, new_y, new_z = 0.20, 0.0, 0.975
    
    mover_client.move_square(new_x, new_y, new_z)
    mover_client.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
