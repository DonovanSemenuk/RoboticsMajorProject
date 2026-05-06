"""Hardware tour launch.

Use this on the physical TurtleBot 4 after running the OU robot bringup and
SLAM/localization.  It intentionally avoids Nav2 actions and drives through
/cmd_vel with odometry feedback, lidar safety halts, and optional keyboard
override on /cmd_vel_key.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    landmarks = LaunchConfiguration("landmarks")
    descriptions = LaunchConfiguration("descriptions")
    initial_x = LaunchConfiguration("initial_x")
    initial_y = LaunchConfiguration("initial_y")
    forward_speed = LaunchConfiguration("forward_speed")
    halt_distance = LaunchConfiguration("halt_distance")
    no_speech = LaunchConfiguration("no_speech")

    return LaunchDescription([
        DeclareLaunchArgument("landmarks", default_value="landmarks/locations.yaml"),
        DeclareLaunchArgument("descriptions", default_value="landmarks/descriptions.yaml"),
        DeclareLaunchArgument("initial_x", default_value="0.0"),
        DeclareLaunchArgument("initial_y", default_value="0.0"),
        DeclareLaunchArgument("forward_speed", default_value="0.12"),
        DeclareLaunchArgument("halt_distance", default_value="0.30"),
        DeclareLaunchArgument("no_speech", default_value="false"),
        Node(
            package="tour_guide",
            executable="hardware_tour_node",
            name="hardware_tour_node",
            arguments=[
                "--landmarks", landmarks,
                "--descriptions", descriptions,
                "--initial-x", initial_x,
                "--initial-y", initial_y,
                "--forward-speed", forward_speed,
                "--halt-distance", halt_distance,
                "--no-speech", no_speech,
            ],
            output="screen",
            emulate_tty=True,
        ),
    ])
