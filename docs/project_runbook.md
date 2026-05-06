# Robot Tour Guide Project Runbook

This runbook turns the assignment and report draft into an actionable checklist for finishing the demonstration, report, and poster.

## Project goal

Build a hybrid TurtleBot 4 tour guide that can rediscover moved tour destinations. The robot uses Nav2 for navigation and adds a deliberative layer that discovers ArUco landmarks, records their map-frame positions, lets an operator choose a tour, optimizes the visiting order, and gives optional spoken commentary.

## Recommended demo story

1. Place four printed ArUco markers at tour stops in the cardboard-city environment.
2. Start the TurtleBot 4 bringup, localization, map, and Nav2.
3. Run discovery so the robot sweeps through the environment and writes `landmarks/locations.yaml`.
4. Show that marker names and descriptions stay editable in `landmarks/descriptions.yaml`.
5. Run tour mode, select a route, accept the optimized order, and let the robot visit each landmark.
6. Move one marker, rerun discovery, and explain that no source-code change was needed.

## Commands

From the workspace root:

```bash
# Install pytest if it is missing in the active environment.
python3 -m pip install pytest

# Run pure Python tests.
PYTHONPATH=src/tour_guide pytest -q src/tour_guide/test/test_selection.py src/tour_guide/test/test_landmark_map.py src/tour_guide/test/test_yaml_io.py

# Build in a ROS 2 environment.
colcon build --symlink-install
source install/setup.bash

# Start the simulation/world/Nav2 stack.
ros2 launch tour_guide launch.py

# In another terminal, run landmark discovery.
ros2 launch tour_guide discover.launch.py

# Run the selected tour after discovery.
ros2 launch tour_guide tour.launch.py
```

For the physical robot, replace the simulation bringup with the OU TurtleBot 4 bringup and the cardboard-city map, then use the same `discover.launch.py` and `tour.launch.py` workflow.

## Data to collect for the final report

Run at least five trials for each condition if time allows.

| Condition | Measurements to record |
| --- | --- |
| Simulation discovery | markers detected, number of observations per marker, sweep time, failures |
| Simulation tour | selected route, optimized distance, completion time, recoveries, collisions |
| Physical discovery | markers detected, missed detections, lighting/occlusion notes, sweep time |
| Physical tour | route completion, arrival accuracy, completion time, recoveries, operator interventions |

Useful summary statistics for the Results section:

- Discovery success rate = successful marker maps / total discovery trials.
- Tour success rate = completed tours / total tour trials.
- Mean completion time and standard deviation.
- Mean marker position repeatability across discovery trials.
- Difference between operator route length and optimized route length.

## Report checklist

- Replace every red `[FILL IN: ...]` in `docs/final_report_draft.tex` with measured data.
- Add screenshots or figures: system diagram, Gazebo world, marker detection image, and route map.
- Make sure every outside code source is credited, especially `ros2_aruco`.
- Include launch/world/source-code appendix information.
- Confirm contributions for Bryan and Donovan before submission.

## Poster checklist

Suggested sections:

- Motivation: fixed waypoint tours break when landmarks move.
- Approach: hybrid architecture diagram with Nav2, ArUco detector, recorder, selector, tour node.
- Demo setup: TurtleBot 4, OAK-D camera, LiDAR/odometry, cardboard city, four markers.
- Results: success-rate table and one route-distance graph.
- Takeaway: relocatable markers make tour stops easier to reconfigure.
