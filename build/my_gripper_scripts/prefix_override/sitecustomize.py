import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/benongnuel/dev_ws/install/my_gripper_scripts'
