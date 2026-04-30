"""Tour phase launch.

Runs the interactive tour: loads the recorded landmark map, prompts the user
for a route, then drives Nav2 through the chosen landmarks. Assumes the
simulator (or real-robot bringup) and Nav2 are already running.

The ArUco detector is launched here too so that markers are still highlighted
in RViz during the tour, but it is not required for navigation.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory("tour_guide")
    default_aruco_params = os.path.join(pkg_share, "config", "aruco_params_sim.yaml")
    default_landmarks = "landmarks/locations.yaml"

    aruco_params = LaunchConfiguration("aruco_params")
    landmarks = LaunchConfiguration("landmarks")

    return LaunchDescription([
        DeclareLaunchArgument("aruco_params", default_value=default_aruco_params),
        DeclareLaunchArgument("landmarks", default_value=default_landmarks,
                              description="Path to the landmark map YAML to tour."),

        Node(
            package="ros2_aruco",
            executable="aruco_node",
            name="aruco_node",
            parameters=[aruco_params],
            output="screen",
        ),
        Node(
            package="tour_guide",
            executable="tour_node",
            name="tour_node",
            arguments=["--landmarks", landmarks],
            output="screen",
            emulate_tty=True,
        ),
    ])
