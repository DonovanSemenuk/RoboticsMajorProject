"""Tour execution node.

Loads the recorded landmark map, merges in any hand-written descriptions,
asks the operator to pick a route (optionally letting the planner reorder it
to minimize travel distance), then drives Nav2 to each landmark in turn while
speaking commentary at every stop.
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

from tour_guide.commentary import make_speaker
from tour_guide.landmark_map import (
    Landmark,
    apply_descriptions,
    load_descriptions,
    load_landmarks,
)
from tour_guide.selection import select_tour


PAUSE_AT_LANDMARK_SEC = 2.0


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


def run_tour(navigator: TurtleBot4Navigator,
             tour: list[Landmark],
             speak) -> None:
    speak("Starting the tour. Please follow me.")
    for step, lm in enumerate(tour, start=1):
        navigator.info(f"Step {step}/{len(tour)}: heading to {lm.display_name}")
        pose = navigator.getPoseStamped(
            [lm.x, lm.y], _yaw_to_direction(lm.yaw)
        )
        navigator.startToPose(pose)

        navigator.info(f"Arrived at {lm.display_name}.")
        speak(f"We have arrived at {lm.display_name}.")
        if lm.description:
            speak(lm.description)
        time.sleep(PAUSE_AT_LANDMARK_SEC)

    navigator.info("Tour complete.")
    speak("That concludes the tour. Thank you for joining.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a tour from a landmark map.")
    parser.add_argument("--landmarks", default="landmarks/locations.yaml",
                        help="Path to the recorded landmark map YAML file")
    parser.add_argument("--descriptions", default="landmarks/descriptions.yaml",
                        help="Path to the optional commentary YAML file")
    parser.add_argument("--initial-x", type=float, default=0.0,
                        help="Initial pose x (must match the robot's spawn)")
    parser.add_argument("--initial-y", type=float, default=0.0,
                        help="Initial pose y")
    parser.add_argument("--no-speech", action="store_true",
                        help="Disable TTS even if a backend is available")
    args, _ = parser.parse_known_args(argv)

    landmarks = load_landmarks(args.landmarks)
    if not landmarks:
        print("No landmarks loaded. Run a sweep first.", file=sys.stderr)
        return 1

    descriptions = load_descriptions(args.descriptions)
    landmarks = apply_descriptions(landmarks, descriptions)

    rclpy.init(args=argv)
    navigator = TurtleBot4Navigator()

    initial_pose = navigator.getPoseStamped(
        [args.initial_x, args.initial_y], TurtleBot4Directions.NORTH
    )
    navigator.setInitialPose(initial_pose)
    navigator.waitUntilNav2Active()

    speak = (lambda _t: None) if args.no_speech else make_speaker(navigator.info)

    navigator.info("Welcome to the tour guide.")
    tour = select_tour(landmarks, start=(args.initial_x, args.initial_y))
    if not tour:
        navigator.info("No tour selected. Exiting.")
        rclpy.shutdown()
        return 0

    run_tour(navigator, tour, speak)
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
