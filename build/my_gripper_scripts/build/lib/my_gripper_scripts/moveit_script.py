import time
import numpy as np
from moveit2_py import MoveGroupInterface, PlanningSceneInterface

def deg2rad(deg):
    return deg * np.pi / 180.0

# Define pre-grasp, grasp, and place joint positions in radians
pre_grasp = [deg2rad(1), deg2rad(-58), deg2rad(-27), deg2rad(0), deg2rad(85), deg2rad(1)]
grasp = [deg2rad(152), deg2rad(20), deg2rad(-104), deg2rad(0), deg2rad(84), deg2rad(152)]
lift = [deg2rad(137), deg2rad(-12), deg2rad(-64), deg2rad(0), deg2rad(76), deg2rad(137)]
place = [deg2rad(135), deg2rad(-8), deg2rad(-68), deg2rad(0), deg2rad(76), deg2rad(135)]

# 1. Create MoveGroup and PlanningScene interfaces
arm = MoveGroupInterface("xarm6", "world")
gripper = MoveGroupInterface("xarm_gripper", "world")
scene = PlanningSceneInterface("world")

# 2. Add a box to the scene
cube_pose = [0.3, 0, 0.05, 0, 0, 0, 1]  # [x, y, z, qx, qy, qz, qw]
scene.add_box("box", cube_pose, [0.05, 0.05, 0.05])

# 3. Open gripper (0 deg)
gripper.set_joint_value_target([deg2rad(0)])
gripper.plan_and_execute()
time.sleep(1)

# 4. Move to pre-grasp pose
arm.set_joint_value_target(pre_grasp)
arm.plan_and_execute()
time.sleep(1)

# 5. Move to grasp pose (over the box)
arm.set_joint_value_target(grasp)
arm.plan_and_execute()
time.sleep(1)

# 6. Close gripper (23 deg)
gripper.set_joint_value_target([deg2rad(23)])
gripper.plan_and_execute()
time.sleep(1)

# 7. Attach box to gripper link (change link name if yours is different)
scene.attach_box("xarm_gripper_base_link", "box")

# 8. Lift the box
arm.set_joint_value_target(lift)
arm.plan_and_execute()
time.sleep(1)

# 9. Move to place pose
arm.set_joint_value_target(place)
arm.plan_and_execute()
time.sleep(1)

# 10. Detach the box (optional)
scene.detach_box("xarm_gripper_base_link", "box")

print("Pick and place complete!")
