from ikpy.chain import Chain

# Load the robot chain from the URDF file
robot_chain = Chain.from_urdf_file("/tmp/xarm6.urdf", base_elements=["link_base"])

# Example: get end-effector position for all joints at zero
joint_angles = [0, 0, 0, 0, 0, 0, 0]  # 7 values: 1 for base, 6 for joints
fk = robot_chain.forward_kinematics(joint_angles)
ee_position = fk[:3, 3]
print("End-effector position:", ee_position)
