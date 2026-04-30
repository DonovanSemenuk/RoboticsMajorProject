"""Tour execution node.

Loads the landmark map, asks the operator to pick a tour route, then drives
Nav2 sequentially to each landmark, pausing briefly at each one.
"""

import argparse
import math
import sys
import time

import rclpy
from turtlebot4_navigation.turtlebot4_navigator import (
    TurtleBot4Navigator,
    TurtleBot4Directions,
)

from tour_guide.landmark_map import Landmark, load_landmarks
from tour_guide.selection import select_tour


PAUSE_AT_LANDMARK_SEC = 5.0


def _yaw_to_direction(yaw: float) -> int:
    """Snap a yaw (radians) to the closest TurtleBot4Directions cardinal."""
    deg = math.degrees(yaw) % 360.0
    if deg < 45 or deg >= 315:
        return TurtleBot4Directions.NORTH
    if deg < 135:
        return TurtleBot4Directions.WEST
    if deg < 225:
        return TurtleBot4Directions.SOUTH
    return TurtleBot4Directions.EAST


def run_tour(navigator: TurtleBot4Navigator, tour: list[Landmark]) -> None:
    for step, lm in enumerate(tour, start=1):
        navigator.info(f"Step {step}/{len(tour)}: heading to {lm.display_name}")
        pose = navigator.getPoseStamped(
            [lm.x, lm.y], _yaw_to_direction(lm.yaw)
        )
        navigator.startToPose(pose)
        navigator.info(f"Arrived at {lm.display_name}. Pausing {PAUSE_AT_LANDMARK_SEC:.0f}s.")
        time.sleep(PAUSE_AT_LANDMARK_SEC)
    navigator.info("Tour complete.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a tour from a landmark map.")
    parser.add_argument(
        "--landmarks",
        default="landmarks/locations.yaml",
        help="Path to the landmark map YAML file",
    )
    args, _ = parser.parse_known_args(argv)

    landmarks = load_landmarks(args.landmarks)
    if not landmarks:
        print("No landmarks loaded. Run a sweep to populate the map first.", file=sys.stderr)
        return 1

    rclpy.init(args=argv)
    navigator = TurtleBot4Navigator()

    initial_pose = navigator.getPoseStamped([0.0, 0.0], TurtleBot4Directions.NORTH)
    navigator.setInitialPose(initial_pose)
    navigator.waitUntilNav2Active()

    navigator.info("Welcome to the tour guide.")
    tour = select_tour(landmarks)
    if not tour:
        navigator.info("No tour selected. Exiting.")
        rclpy.shutdown()
        return 0

    run_tour(navigator, tour)
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
