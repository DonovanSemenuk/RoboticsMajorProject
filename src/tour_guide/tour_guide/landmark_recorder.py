"""Landmark recorder.

Subscribes to ArUco marker detections, transforms each detected marker pose from
the camera frame into the map frame, and maintains a running average pose per
marker id. Writes the accumulated landmark map to YAML on a fixed cadence and
on shutdown.

Designed to run alongside the sweep node: the sweep drives the robot around so
the camera can see markers, this node records them.
"""

import math
import os
from dataclasses import dataclass
from typing import Dict

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.qos import qos_profile_sensor_data

import tf2_ros
from tf2_geometry_msgs import do_transform_pose
from geometry_msgs.msg import Pose
from visualization_msgs.msg import Marker, MarkerArray

from ros2_aruco_interfaces.msg import ArucoMarkers

from tour_guide.landmark_map import Landmark, save_landmarks


@dataclass
class _RunningPose:
    """Incremental mean of (x, y) and circular mean of yaw for one marker."""
    n: int = 0
    x: float = 0.0
    y: float = 0.0
    sin_yaw: float = 0.0
    cos_yaw: float = 0.0

    def update(self, x: float, y: float, yaw: float) -> None:
        self.n += 1
        self.x += (x - self.x) / self.n
        self.y += (y - self.y) / self.n
        self.sin_yaw += (math.sin(yaw) - self.sin_yaw) / self.n
        self.cos_yaw += (math.cos(yaw) - self.cos_yaw) / self.n

    def yaw(self) -> float:
        return math.atan2(self.sin_yaw, self.cos_yaw)


def _yaw_from_quat(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class LandmarkRecorder(Node):
    def __init__(self):
        super().__init__("landmark_recorder")

        self.declare_parameter("map_frame", "map")
        self.declare_parameter("output_path", "landmarks/locations.yaml")
        self.declare_parameter("save_period_sec", 2.0)
        self.declare_parameter("min_observations", 3)
        self.declare_parameter("tf_timeout_sec", 0.2)

        self.map_frame = self.get_parameter("map_frame").value
        self.output_path = self.get_parameter("output_path").value
        save_period = float(self.get_parameter("save_period_sec").value)
        self.min_observations = int(self.get_parameter("min_observations").value)
        self.tf_timeout = Duration(
            seconds=float(self.get_parameter("tf_timeout_sec").value)
        )

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.markers_sub = self.create_subscription(
            ArucoMarkers,
            "/aruco_markers",
            self._on_markers,
            qos_profile_sensor_data,
        )

        self.markers_pub = self.create_publisher(
            MarkerArray, "/tour_guide/landmarks", 10
        )

        self.estimates: Dict[int, _RunningPose] = {}
        self.save_timer = self.create_timer(save_period, self._save)
        self.viz_timer = self.create_timer(0.5, self._publish_viz)

        self.get_logger().info(
            f"landmark_recorder ready (map_frame={self.map_frame}, "
            f"output={self.output_path}, save_period={save_period}s, "
            f"min_obs={self.min_observations})"
        )

    def _on_markers(self, msg: ArucoMarkers) -> None:
        camera_frame = msg.header.frame_id
        if not camera_frame:
            self.get_logger().warn("ArucoMarkers msg has empty frame_id; skipping")
            return

        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                camera_frame,
                msg.header.stamp,
                self.tf_timeout,
            )
        except (tf2_ros.LookupException,
                tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException) as e:
            self.get_logger().warn(
                f"TF {camera_frame} -> {self.map_frame} unavailable: {e}",
                throttle_duration_sec=2.0,
            )
            return

        for marker_id, pose in zip(msg.marker_ids, msg.poses):
            mapped: Pose = do_transform_pose(pose, transform)
            yaw = _yaw_from_quat(mapped.orientation)
            est = self.estimates.setdefault(int(marker_id), _RunningPose())
            est.update(mapped.position.x, mapped.position.y, yaw)

    def _confirmed_landmarks(self):
        return [
            Landmark(
                id=mid,
                x=est.x,
                y=est.y,
                yaw=est.yaw(),
                name=f"Landmark {mid}",
            )
            for mid, est in sorted(self.estimates.items())
            if est.n >= self.min_observations
        ]

    def _save(self) -> None:
        landmarks = self._confirmed_landmarks()
        if not landmarks:
            return
        save_landmarks(self.output_path, landmarks)
        self.get_logger().info(
            f"Saved {len(landmarks)} landmark(s) to {os.path.abspath(self.output_path)}"
        )

    def _publish_viz(self) -> None:
        landmarks = self._confirmed_landmarks()
        if not landmarks:
            return
        msg = MarkerArray()
        for lm in landmarks:
            cube = Marker()
            cube.header.frame_id = self.map_frame
            cube.header.stamp = self.get_clock().now().to_msg()
            cube.ns = "landmarks"
            cube.id = lm.id * 2
            cube.type = Marker.CUBE
            cube.action = Marker.ADD
            cube.pose.position.x = lm.x
            cube.pose.position.y = lm.y
            cube.pose.position.z = 0.15
            cube.pose.orientation.w = 1.0
            cube.scale.x = cube.scale.y = cube.scale.z = 0.25
            cube.color.r = 0.1
            cube.color.g = 0.8
            cube.color.b = 0.2
            cube.color.a = 0.85
            msg.markers.append(cube)

            label = Marker()
            label.header = cube.header
            label.ns = "landmark_labels"
            label.id = lm.id * 2 + 1
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose.position.x = lm.x
            label.pose.position.y = lm.y
            label.pose.position.z = 0.5
            label.pose.orientation.w = 1.0
            label.scale.z = 0.25
            label.color.r = label.color.g = label.color.b = label.color.a = 1.0
            label.text = lm.display_name
            msg.markers.append(label)
        self.markers_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LandmarkRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._save()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
