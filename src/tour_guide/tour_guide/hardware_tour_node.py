"""Direct hardware tour driver for TurtleBot 4.

This node is a fallback for real-robot demonstrations where the full Nav2 tour
stack is not available or is too brittle.  It borrows the proven hardware
interfaces from Bryan Tran's Project 2 controller: publish ``TwistStamped`` to
``/cmd_vel``, allow keyboard override through ``/cmd_vel_key``, use odometry for
yaw/distance feedback, and stop whenever lidar reports a close obstacle.

The node still uses this project's landmark map and route-selection code, so it
can execute an actual landmark tour without editing the external Project 2
repository.
"""

import argparse
import math
import sys
import time
from typing import Optional

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

from tour_guide.commentary import make_speaker
from tour_guide.landmark_map import apply_descriptions, load_descriptions, load_landmarks
from tour_guide.selection import select_tour


KEY_TIMEOUT_SEC = 0.3
DEFAULT_FORWARD_SPEED = 0.12
DEFAULT_TURN_SPEED = 0.35
DEFAULT_GOAL_TOLERANCE_M = 0.18
DEFAULT_YAW_TOLERANCE_RAD = math.radians(8.0)
DEFAULT_HALT_DISTANCE_M = 0.30
DEFAULT_FRONT_ARC_RAD = math.radians(30.0)
DEFAULT_PAUSE_SEC = 2.0


def quat_to_yaw(q) -> float:
    """Extract yaw, in radians, from a ROS quaternion."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def normalize_angle(angle: float) -> float:
    """Wrap an angle to [-pi, pi]."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def shortest_yaw_error(target: float, current: float) -> float:
    """Return the shortest signed angular error from current yaw to target yaw."""
    return normalize_angle(target - current)


def make_stamped_twist(node: Node, twist: Twist) -> TwistStamped:
    """Wrap a Twist command in the stamped command format used by TurtleBot 4."""
    stamped = TwistStamped()
    stamped.header.stamp = node.get_clock().now().to_msg()
    stamped.twist = twist
    return stamped


class HardwareTourNode(Node):
    """Execute a landmark tour with odometry feedback and lidar safety stops."""

    def __init__(self, args):
        super().__init__("hardware_tour_node")
        self.args = args

        self.cmd_pub = self.create_publisher(TwistStamped, "/cmd_vel", 10)
        self.create_subscription(Twist, "/cmd_vel_key", self._on_key, 10)
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)
        self.create_subscription(LaserScan, "/scan", self._on_scan, 10)

        self.x: Optional[float] = None
        self.y: Optional[float] = None
        self.yaw = 0.0
        self.halt_active = False
        self.key_active = False
        self.key_last_time = 0.0
        self.last_key_cmd = Twist()

    def _on_key(self, msg: Twist) -> None:
        """Record keyboard commands so an operator can immediately take over."""
        self.last_key_cmd = msg
        self.key_last_time = self.get_clock().now().nanoseconds / 1e9
        self.key_active = msg.linear.x != 0.0 or msg.angular.z != 0.0

    def _on_odom(self, msg: Odometry) -> None:
        """Track robot pose in the odom frame."""
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.yaw = quat_to_yaw(msg.pose.pose.orientation)

    def _on_scan(self, msg: LaserScan) -> None:
        """Stop on any close obstacle and warn on close obstacles ahead."""
        too_close = False
        front_close = False
        for i, distance in enumerate(msg.ranges):
            if math.isinf(distance) or math.isnan(distance) or distance <= 0.0:
                continue
            if distance < msg.range_min or distance > msg.range_max:
                continue
            if distance < self.args.halt_distance:
                too_close = True
            angle = normalize_angle(msg.angle_min + i * msg.angle_increment)
            if abs(angle) <= self.args.front_arc and distance < self.args.halt_distance * 1.5:
                front_close = True

        if too_close and not self.halt_active:
            self.get_logger().info(
                f"Safety halt: obstacle within {self.args.halt_distance:.2f} m."
            )
        if front_close:
            self.get_logger().debug("Obstacle detected in front arc.")
        self.halt_active = too_close

    def _publish(self, twist: Twist) -> None:
        self.cmd_pub.publish(make_stamped_twist(self, twist))

    def _stop(self) -> None:
        self._publish(Twist())

    def _spin_once(self) -> None:
        rclpy.spin_once(self, timeout_sec=0.05)
        now = self.get_clock().now().nanoseconds / 1e9
        if self.key_active and (now - self.key_last_time) > KEY_TIMEOUT_SEC:
            self.key_active = False

    def _wait_for_odom(self) -> bool:
        self.get_logger().info("Waiting for /odom before starting hardware tour...")
        deadline = time.time() + self.args.odom_timeout
        while rclpy.ok() and time.time() < deadline:
            self._spin_once()
            if self.x is not None and self.y is not None:
                return True
        self.get_logger().error("Timed out waiting for /odom.")
        return False

    def _safety_or_keyboard_active(self) -> bool:
        if self.halt_active:
            self._stop()
            self.get_logger().info(
                "Safety halt active; waiting for obstacle to clear.",
                throttle_duration_sec=1.0,
            )
            return True
        if self.key_active:
            self._publish(self.last_key_cmd)
            return True
        return False

    def drive_to(self, goal_x: float, goal_y: float) -> bool:
        """Drive toward an odom-frame goal using a simple proportional controller."""
        start_time = time.time()
        while rclpy.ok():
            self._spin_once()
            if self._safety_or_keyboard_active():
                continue
            if self.x is None or self.y is None:
                self._stop()
                continue

            dx = goal_x - self.x
            dy = goal_y - self.y
            distance = math.hypot(dx, dy)
            if distance <= self.args.goal_tolerance:
                self._stop()
                return True
            if time.time() - start_time > self.args.goal_timeout:
                self._stop()
                self.get_logger().error(
                    f"Timed out before reaching ({goal_x:.2f}, {goal_y:.2f})."
                )
                return False

            target_yaw = math.atan2(dy, dx)
            yaw_error = shortest_yaw_error(target_yaw, self.yaw)
            cmd = Twist()
            if abs(yaw_error) > self.args.yaw_tolerance:
                cmd.angular.z = max(
                    -self.args.turn_speed,
                    min(self.args.turn_speed, 1.5 * yaw_error),
                )
            else:
                cmd.linear.x = min(self.args.forward_speed, 0.5 * distance)
                cmd.angular.z = max(
                    -self.args.turn_speed,
                    min(self.args.turn_speed, 1.0 * yaw_error),
                )
            self._publish(cmd)

        self._stop()
        return False

    def run_route(self, tour, speak) -> bool:
        """Run a complete landmark route."""
        if not self._wait_for_odom():
            return False

        offset_x = self.x - self.args.initial_x
        offset_y = self.y - self.args.initial_y
        self.get_logger().info(
            "Using odom/map offset "
            f"({offset_x:.2f}, {offset_y:.2f}) from initial pose "
            f"({self.args.initial_x:.2f}, {self.args.initial_y:.2f})."
        )

        speak("Starting the hardware tour. Please follow me.")
        for step, landmark in enumerate(tour, start=1):
            goal_x = landmark.x + offset_x
            goal_y = landmark.y + offset_y
            self.get_logger().info(
                f"Hardware tour step {step}/{len(tour)}: "
                f"driving to {landmark.display_name} at "
                f"map=({landmark.x:.2f}, {landmark.y:.2f}), "
                f"odom=({goal_x:.2f}, {goal_y:.2f})."
            )
            if not self.drive_to(goal_x, goal_y):
                speak(f"I could not safely reach {landmark.display_name}.")
                return False
            speak(f"We have arrived at {landmark.display_name}.")
            if landmark.description:
                speak(landmark.description)
            end_pause = time.time() + self.args.pause
            while rclpy.ok() and time.time() < end_pause:
                self._stop()
                self._spin_once()

        self._stop()
        speak("That concludes the tour. Thank you for joining.")
        return True


def _bool_arg(value) -> bool:
    """Parse ROS launch-friendly boolean strings."""
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    raise argparse.ArgumentTypeError(f"expected a boolean, got {value!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a direct odometry/lidar hardware tour from landmarks.yaml."
    )
    parser.add_argument("--landmarks", default="landmarks/locations.yaml")
    parser.add_argument("--descriptions", default="landmarks/descriptions.yaml")
    parser.add_argument("--initial-x", type=float, default=0.0)
    parser.add_argument("--initial-y", type=float, default=0.0)
    parser.add_argument("--forward-speed", type=float, default=DEFAULT_FORWARD_SPEED)
    parser.add_argument("--turn-speed", type=float, default=DEFAULT_TURN_SPEED)
    parser.add_argument("--goal-tolerance", type=float, default=DEFAULT_GOAL_TOLERANCE_M)
    parser.add_argument("--yaw-tolerance", type=float, default=DEFAULT_YAW_TOLERANCE_RAD)
    parser.add_argument("--halt-distance", type=float, default=DEFAULT_HALT_DISTANCE_M)
    parser.add_argument("--front-arc", type=float, default=DEFAULT_FRONT_ARC_RAD)
    parser.add_argument("--goal-timeout", type=float, default=90.0)
    parser.add_argument("--odom-timeout", type=float, default=10.0)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_SEC)
    parser.add_argument("--no-speech", nargs="?", const=True, default=False, type=_bool_arg)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args, _ = parser.parse_known_args(argv)

    landmarks = load_landmarks(args.landmarks)
    if not landmarks:
        print("No landmarks loaded. Run discovery or edit locations.yaml first.", file=sys.stderr)
        return 1
    landmarks = apply_descriptions(landmarks, load_descriptions(args.descriptions))

    route = select_tour(landmarks, start=(args.initial_x, args.initial_y))
    if not route:
        print("No tour selected.")
        return 0

    rclpy.init(args=argv)
    node = HardwareTourNode(args)
    speak = (lambda _text: None) if args.no_speech else make_speaker(node.get_logger().info)
    try:
        return 0 if node.run_route(route, speak) else 2
    finally:
        node._stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
