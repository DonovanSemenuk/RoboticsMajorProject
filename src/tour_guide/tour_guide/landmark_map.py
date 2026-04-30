"""Landmark map I/O.

Defines the contract between the sweep node (writes) and the tour node (reads).
A landmark is an ArUco marker that has been detected and localized in the map frame.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
import yaml


@dataclass
class Landmark:
    id: int
    x: float
    y: float
    yaw: float
    name: Optional[str] = None

    @property
    def display_name(self) -> str:
        return self.name if self.name else f"Marker {self.id}"


def load_landmarks(path: str) -> List[Landmark]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Landmark file not found: {path}")

    with open(p, "r") as f:
        data = yaml.safe_load(f) or {}

    raw = data.get("landmarks", [])
    landmarks = []
    for entry in raw:
        landmarks.append(Landmark(
            id=int(entry["id"]),
            x=float(entry["x"]),
            y=float(entry["y"]),
            yaw=float(entry.get("yaw", 0.0)),
            name=entry.get("name"),
        ))
    return landmarks


def save_landmarks(path: str, landmarks: List[Landmark]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"landmarks": [asdict(lm) for lm in landmarks]}
    with open(p, "w") as f:
        yaml.safe_dump(payload, f, sort_keys=False)
