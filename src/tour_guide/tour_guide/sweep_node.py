"""Autonomous sweep node.

Drives the robot through a sequence of pre-recorded sweep waypoints using Nav2,
performing a full 360-degree spin at each one so the camera can see markers in
every direction. Run this together with the landmark_recorder node.

The waypoints define an exploration path; they are environment-specific and
should cover all areas where ArUco markers might be placed.
"""

import argparse
import math
import sys
from pathlib import Path
from typing import List, Tuple

import yaml

import rclpy
from turtlebot4_navigation.turtlebot4_navigator import (
    TurtleBot4Navigator,
    TurtleBot4Directions,
)


SPIN_HEADINGS = (
    TurtleBot4Directions.NORTH,
    TurtleBot4Directions.WEST,
    TurtleBot4Directions.SOUTH,
    TurtleBot4Directions.EAST,
)


def load_waypoints(path: str) -> List[Tuple[float, float]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Sweep waypoint file not found: {path}")
    with open(p, "r") as f:
        data = yaml.safe_load(f) or {}
    raw = data.get("waypoints", [])
    return [(float(w["x"]), float(w["y"])) for w in raw]


def sweep_at(navigator: TurtleBot4Navigator, x: float, y: float) -> None:
    """Drive to (x, y) and rotate through the four cardinal headings."""
    for heading in SPIN_HEADINGS:
        pose = navigator.getPoseStamped([x, y], heading)
        navigator.startToPose(pose)


def run_sweep(navigator: TurtleBot4Navigator,
              waypoints: List[Tuple[float, float]]) -> None:
    for i, (x, y) in enumerate(waypoints, start=1):
        navigator.info(f"Sweep waypoint {i}/{len(waypoints)}: ({x:.2f}, {y:.2f})")
        sweep_at(navigator, x, y)
    navigator.info("Sweep complete.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Autonomous sweep over a list of waypoints.")
    parser.add_argument(
        "--waypoints",
        default="src/tour_guide/config/sweep_waypoints.yaml",
        help="Path to the sweep waypoints YAML file",
    )
    parser.add_argument(
        "--initial-x", type=float, default=0.0,
        help="Initial pose x (must match where the robot is spawned)",
    )
    parser.add_argument(
        "--initial-y", type=float, default=0.0,
        help="Initial pose y",
    )
    args, _ = parser.parse_known_args(argv)

    waypoints = load_waypoints(args.waypoints)
    if not waypoints:
        print("No sweep waypoints loaded. Nothing to do.", file=sys.stderr)
        return 1

    rclpy.init(args=argv)
    navigator = TurtleBot4Navigator()

    initial_pose = navigator.getPoseStamped(
        [args.initial_x, args.initial_y], TurtleBot4Directions.NORTH
    )
    navigator.setInitialPose(initial_pose)
    navigator.waitUntilNav2Active()

    run_sweep(navigator, waypoints)
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
