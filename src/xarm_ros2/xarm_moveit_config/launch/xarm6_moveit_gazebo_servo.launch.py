from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    hw_ns = LaunchConfiguration('hw_ns', default='xarm')

    # Include Gazebo + MoveIt
    robot_moveit_gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('xarm_moveit_config'),
                'launch',
                'xarm6_moveit_gazebo.launch.py'
            ])
        ),
        launch_arguments={
            'hw_ns': hw_ns,
        }.items(),
    )

    # Include MoveIt Servo
    moveit_servo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('xarm_moveit_servo'),
                'launch',
                'xarm_moveit_servo_fake.launch.py'
            ])
        ),
        launch_arguments={
            'dof': '6',
            'robot_type': 'xarm',
            'hw_ns': hw_ns,
        }.items(),
    )

    return LaunchDescription([
        robot_moveit_gazebo_launch,
        moveit_servo_launch
    ])
