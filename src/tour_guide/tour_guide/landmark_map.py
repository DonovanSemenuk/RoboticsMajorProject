"""Landmark map I/O.

Defines the contract between the sweep node (writes locations.yaml) and the
tour node (reads it). A landmark is an ArUco marker that has been detected and
localized in the map frame.

Optional descriptions live in a separate YAML so that the recorder can keep
overwriting locations.yaml without trampling hand-written tour commentary.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class Landmark:
    id: int
    x: float
    y: float
    yaw: float
    name: Optional[str] = None
    description: Optional[str] = None

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
            description=entry.get("description"),
        ))
    return landmarks


def save_landmarks(path: str, landmarks: List[Landmark]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"landmarks": [
        {k: v for k, v in asdict(lm).items() if v is not None or k in ("id", "x", "y", "yaw")}
        for lm in landmarks
    ]}
    with open(p, "w") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def load_descriptions(path: str) -> Dict[int, Dict[str, str]]:
    """Load per-marker tour commentary keyed by marker id.

    Returns an empty dict if the file is missing -- descriptions are optional.
    """
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r") as f:
        data = yaml.safe_load(f) or {}
    out: Dict[int, Dict[str, str]] = {}
    for entry in data.get("descriptions", []):
        mid = int(entry["id"])
        out[mid] = {
            "name": entry.get("name"),
            "description": entry.get("description"),
        }
    return out


def apply_descriptions(landmarks: List[Landmark],
                       descriptions: Dict[int, Dict[str, str]]) -> List[Landmark]:
    """Return new Landmark list with names/descriptions merged in by id."""
    enriched = []
    for lm in landmarks:
        meta = descriptions.get(lm.id, {})
        enriched.append(Landmark(
            id=lm.id,
            x=lm.x,
            y=lm.y,
            yaw=lm.yaw,
            name=meta.get("name") or lm.name,
            description=meta.get("description") or lm.description,
        ))
    return enriched
