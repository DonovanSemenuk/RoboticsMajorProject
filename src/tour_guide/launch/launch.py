from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, EnvironmentVariable
from ament_index_python.packages import get_package_share_directory, PackageNotFoundError
import os


def _tb4_sim_launch() -> str:
    for pkg, filename in (
        ('turtlebot4_gz_bringup', 'gz.launch.py'),
        ('turtlebot4_ignition_bringup', 'ignition.launch.py'),
    ):
        try:
            share = get_package_share_directory(pkg)
            path = os.path.join(share, 'launch', filename)
            if os.path.isfile(path):
                return path
        except PackageNotFoundError:
            continue
    raise RuntimeError(
        'Neither turtlebot4_gz_bringup nor turtlebot4_ignition_bringup is installed. '
        'Install one of them before launching the tour-guide simulation.'
    )


def generate_launch_description():
    pkg_share = get_package_share_directory('tour_guide')

    default_world = os.path.join(pkg_share, 'worlds', 'tour_world.sdf')
    default_map = os.path.join(pkg_share, 'maps', 'sim.yaml')
    models_dir = os.path.join(pkg_share, 'models')
    worlds_dir = os.path.join(pkg_share, 'worlds')

    tb4_sim_launch = _tb4_sim_launch()

    return LaunchDescription([
        SetEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            [models_dir, ':', worlds_dir, ':',
             EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value='')],
        ),
        SetEnvironmentVariable(
            'IGN_GAZEBO_RESOURCE_PATH',
            [models_dir, ':', worlds_dir, ':',
             EnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', default_value='')],
        ),

        DeclareLaunchArgument('world', default_value=default_world,
                              description='Path to the Gazebo world SDF file.'),
        DeclareLaunchArgument('map', default_value=default_map,
                              description='Path to the Nav2 map YAML file.'),
        DeclareLaunchArgument('slam', default_value='False',
                              description='Run SLAM instead of loading a static map.'),
        DeclareLaunchArgument('rviz', default_value='True',
                              description='Launch RViz2.'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(tb4_sim_launch),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'map':   LaunchConfiguration('map'),
                'slam':  LaunchConfiguration('slam'),
                'rviz':  LaunchConfiguration('rviz'),
                'x':   '1.0',
                'y':   '3.0',
                'z':   '0.0',
                'yaw': '0.0',
            }.items(),
        ),
    ])