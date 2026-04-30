"""Discovery phase launch.

Brings up the ArUco detector, the landmark recorder, and the autonomous sweep
node. Assumes the simulator (or real-robot bringup) and Nav2 are already
running -- launch tour_guide/launch/launch.py first.

The sweep node drives the robot through a list of waypoints, rotating at each
one, while the recorder writes detected markers to landmarks/locations.yaml.
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
    default_waypoints = os.path.join(pkg_share, "config", "sweep_waypoints.yaml")
    default_output = "landmarks/locations.yaml"

    aruco_params = LaunchConfiguration("aruco_params")
    waypoints = LaunchConfiguration("waypoints")
    output_path = LaunchConfiguration("output_path")
    initial_x = LaunchConfiguration("initial_x")
    initial_y = LaunchConfiguration("initial_y")

    return LaunchDescription([
        DeclareLaunchArgument("aruco_params", default_value=default_aruco_params,
                              description="Path to ros2_aruco parameters YAML."),
        DeclareLaunchArgument("waypoints", default_value=default_waypoints,
                              description="Path to sweep waypoints YAML."),
        DeclareLaunchArgument("output_path", default_value=default_output,
                              description="Where landmark_recorder writes the landmark map."),
        DeclareLaunchArgument("initial_x", default_value="1.0",
                              description="Initial robot x (must match the sim spawn)."),
        DeclareLaunchArgument("initial_y", default_value="3.0",
                              description="Initial robot y."),

        Node(
            package="ros2_aruco",
            executable="aruco_node",
            name="aruco_node",
            parameters=[aruco_params],
            output="screen",
        ),
        Node(
            package="tour_guide",
            executable="landmark_recorder",
            name="landmark_recorder",
            parameters=[{"output_path": output_path}],
            output="screen",
        ),
        Node(
            package="tour_guide",
            executable="sweep_node",
            name="sweep_node",
            arguments=[
                "--waypoints", waypoints,
                "--initial-x", initial_x,
                "--initial-y", initial_y,
            ],
            output="screen",
        ),
    ])
