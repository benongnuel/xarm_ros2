from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Launch Gazebo with your custom world
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('gazebo_ros'),
                'launch',
                'gazebo.launch.py'
            ])
        ),
        launch_arguments={
            'world': PathJoinSubstitution([
                FindPackageShare('xarm_gazebo'),
                'worlds',
                'aircraft_sheet.world'
            ])
        }.items()
    )

    # Launch your robot MoveIt + Gazebo integration (assuming you have _robot_moveit_gazebo.launch.py)
    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('xarm_moveit_config'),
                'launch',
                '_robot_moveit_gazebo.launch.py'
            ])
        ),
        launch_arguments={
            'dof': '6',
            'robot_type': 'xarm',
            'hw_ns': 'xarm',
            'no_gui_ctrl': 'false',
        }.items()
    )

    return LaunchDescription([
        robot
    ])
