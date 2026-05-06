# Robotics Major Project: TurtleBot 4 Robot Tour Guide

This workspace implements a hybrid ROS 2 tour-guide system for the OU TurtleBot 4. The robot uses Nav2 for low-level navigation and an original deliberative layer for discovering relocatable ArUco landmarks, building a landmark map, selecting a tour route, optimizing the visiting order, and delivering optional commentary.

## Repository layout

- `src/tour_guide/` — main ROS 2 package for discovery, landmark recording, route selection, and tour execution.
- `src/ros2_aruco/` — ArUco detection package used by the project.
- `landmarks/locations.yaml` — recorded marker locations used by tour mode.
- `landmarks/descriptions.yaml` — hand-written landmark names and spoken descriptions.
- `markers/` — printable ArUco marker images and marker-generation script.
- `docs/final_report_draft.tex` — report draft aligned with the assignment requirements.
- `docs/project_runbook.md` — demonstration, testing, report, and poster checklist.

## Basic workflow

1. Bring up the TurtleBot 4 simulation or physical robot with localization and Nav2.
2. Run discovery with `ros2 launch tour_guide discover.launch.py` to sweep the environment and record marker locations.
3. Edit `landmarks/descriptions.yaml` if the marker names or commentary should change.
4. Run Nav2 tour mode with `ros2 launch tour_guide tour.launch.py` and select the desired route at the prompt.
5. On hardware, if Nav2 waypoint touring is unreliable, run the direct odometry/lidar driver with `ros2 launch tour_guide hardware_tour.launch.py`. This fallback publishes TurtleBot 4 `TwistStamped` commands on `/cmd_vel`, honors keyboard override on `/cmd_vel_key`, and stops on close lidar obstacles. For manual override, run `ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r /cmd_vel:=/cmd_vel_key`.

See `docs/project_runbook.md` for detailed commands and the final-report data-collection checklist.

## Hardware fallback note

The hardware fallback was adapted from the team's working Project 2 controller patterns: stamped velocity commands, odometry yaw feedback, `/scan` safety halts, and `/cmd_vel_key` keyboard priority. The external Project 2 repository is used only as a reference; this repository contains the integrated implementation.
