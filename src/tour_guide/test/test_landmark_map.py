"""Tests for landmark map I/O and description merging."""

import pytest

from tour_guide.landmark_map import (
    Landmark,
    apply_descriptions,
    load_descriptions,
    load_landmarks,
    save_landmarks,
)


def test_landmark_display_name_falls_back_to_id():
    lm = Landmark(id=7, x=0.0, y=0.0, yaw=0.0)
    assert lm.display_name == "Marker 7"


def test_landmark_display_name_uses_name_when_set():
    lm = Landmark(id=7, x=0.0, y=0.0, yaw=0.0, name="Atrium")
    assert lm.display_name == "Atrium"


def test_save_omits_none_optional_fields(tmp_path):
    path = tmp_path / "out.yaml"
    save_landmarks(str(path), [Landmark(id=0, x=1.0, y=2.0, yaw=0.0)])
    text = path.read_text()
    assert "name" not in text
    assert "description" not in text


def test_load_descriptions_missing_file_returns_empty(tmp_path):
    assert load_descriptions(str(tmp_path / "nope.yaml")) == {}


def test_load_descriptions_parses_entries(tmp_path):
    path = tmp_path / "desc.yaml"
    path.write_text(
        "descriptions:\n"
        "  - id: 0\n    name: Lobby\n    description: Welcome.\n"
        "  - id: 2\n    name: Lab\n    description: This is the lab.\n"
    )
    descs = load_descriptions(str(path))
    assert descs[0]["name"] == "Lobby"
    assert descs[2]["description"] == "This is the lab."


def test_apply_descriptions_overrides_name_and_adds_description():
    landmarks = [
        Landmark(id=0, x=0.0, y=0.0, yaw=0.0, name="Marker 0"),
        Landmark(id=1, x=1.0, y=1.0, yaw=0.0),
    ]
    descs = {0: {"name": "Lobby", "description": "Welcome."}}
    enriched = apply_descriptions(landmarks, descs)
    assert enriched[0].name == "Lobby"
    assert enriched[0].description == "Welcome."
    # Untouched entries pass through unchanged.
    assert enriched[1].name is None
    assert enriched[1].description is None


def test_apply_descriptions_does_not_mutate_input():
    landmarks = [Landmark(id=0, x=0.0, y=0.0, yaw=0.0)]
    apply_descriptions(landmarks, {0: {"name": "X", "description": "Y"}})
    assert landmarks[0].name is None


def test_real_descriptions_file_parses():
    descs = load_descriptions("landmarks/descriptions.yaml")
    assert isinstance(descs, dict)
    if descs:
        for mid, meta in descs.items():
            assert isinstance(mid, int)
            assert "name" in meta
            assert "description" in meta
