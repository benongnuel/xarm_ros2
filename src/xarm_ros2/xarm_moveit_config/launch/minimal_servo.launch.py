from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    robot_description_content = Command([
    'xacro ',
    PathJoinSubstitution([
        FindPackageShare('xarm_description'),
        'urdf',
        'xarm6',
        'xarm6.urdf.xacro'
    ])
])
    
    robot_description = {'robot_description': robot_description_content}

    robot_description_semantic_content = Command([
        'xacro ',
        PathJoinSubstitution([
            FindPackageShare('xarm_moveit_config'),
            'srdf',
            'xarm.srdf.xacro'
        ])
    ])
    robot_description_semantic = {'robot_description_semantic': robot_description_semantic_content}

    return LaunchDescription([
        Node(
            package='moveit_servo',
            executable='servo_node_main',
            name='servo_server',
            output='screen',
            parameters=[
                robot_description,
                robot_description_semantic,
                '/home/benongnuel/dev_ws/src/xarm_ros2/xarm_moveit_servo/config/xarm_moveit_servo_config.yaml'
            ]
        )
    ])