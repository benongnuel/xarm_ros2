import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
import numpy as np
import time

class SimplePBVSZ(Node):
    def __init__(self):
        super().__init__('simple_pbvs_z')
        self.ball_pose = None
        self.current_joints = None
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']
        self.create_subscription(PoseStamped, '/red_ball_pose', self.ball_cb, 10)
        self.create_subscription(JointState, '/joint_states', self.joint_cb, 10)
        self.cmd_pub = self.create_publisher(Float64MultiArray, '/xarm6_velocity_controller/commands', 10)
        self.timer = self.create_timer(0.1, self.control_loop)  # 10 Hz

        # Sweep/search parameters
        self.sweep_direction = 1
        self.sweep_timer = time.time()
        self.sweep_duration = 2.0  # seconds in one direction

        # Ball lost timeout
        self.last_ball_time = 0
        self.ball_timeout = 1.0  # seconds to consider ball lost

        # Search pose for all joints (adjust as needed for your robot)
        self.search_pose = np.array([0.5, 0.6, 0.5, 0.5, 0.5, 0.5])  # [joint1, joint2, joint3, joint4, joint5, joint6]

    def ball_cb(self, msg):
        self.ball_pose = msg
        self.last_ball_time = time.time()

    def joint_cb(self, msg):
        joint_pos = [0.0]*6
        for i, name in enumerate(self.joint_names):
            if name in msg.name:
                idx = msg.name.index(name)
                joint_pos[i] = msg.position[idx]
        self.current_joints = np.array(joint_pos)

    def control_loop(self):
        now = time.time()
        ball_visible = self.ball_pose is not None and (now - self.last_ball_time) < self.ball_timeout

        vel_cmd = np.zeros(6)

        if self.current_joints is None:
            return

        if ball_visible:
            # PBVS z-control: move joint3 to keep camera 25cm above ball
            current_z = self.current_joints[2]
            desired_z = self.ball_pose.pose.position.z + 0.25
            error_z = desired_z - current_z
            gain_z = 0.5
            vel_cmd[2] = np.clip(-gain_z * error_z, -0.5, 0.5)

            # Hold all other joints at search pose (except joint1, which is held at current value)
            for i in [1, 3, 4, 5]:
                error = self.search_pose[i] - self.current_joints[i]
                vel_cmd[i] = np.clip(0.5 * error, -0.5, 0.5)
            vel_cmd[0] = 0.0  # Hold joint1 at current value during tracking

        else:
            # Hold all joints at search pose
            error_vec = self.search_pose - self.current_joints
            vel_cmd = np.clip(0.5 * error_vec, -0.5, 0.5)
            # Sweep joint1
            if now - self.sweep_timer > self.sweep_duration:
                self.sweep_direction *= -1
                self.sweep_timer = now
            vel_cmd[0] = 0.3 * self.sweep_direction  # Override joint1 for sweeping

        msg = Float64MultiArray()
        msg.data = vel_cmd.tolist()
        self.cmd_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SimplePBVSZ()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()