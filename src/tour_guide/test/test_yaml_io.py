"""Tests for the small project YAML reader/writer."""

from io import StringIO

from tour_guide import yaml_io


def test_safe_load_parses_indented_list_items_with_comments():
    data = yaml_io.safe_load(
        "# Tour descriptions\n"
        "descriptions:\n"
        "  - id: 0\n"
        "    name: \"Reception Desk\"\n"
        "    description: \"Welcome: check in here.\"  # keep colon\n"
    )
    assert data["descriptions"][0]["id"] == 0
    assert data["descriptions"][0]["name"] == "Reception Desk"
    assert data["descriptions"][0]["description"] == "Welcome: check in here."


def test_safe_load_parses_inline_waypoint_maps():
    data = yaml_io.safe_load(
        "waypoints:\n"
        "  - { x: 1.0, y: 1.0 }\n"
        "  - { x: 2.5, y: -3.0 }\n"
    )
    assert data == {"waypoints": [{"x": 1.0, "y": 1.0}, {"x": 2.5, "y": -3.0}]}


def test_safe_dump_round_trips_simple_landmarks():
    out = StringIO()
    yaml_io.safe_dump(
        {"landmarks": [{"id": 2, "name": "Lab", "x": 1.25, "y": 2.5}]},
        out,
    )
    loaded = yaml_io.safe_load(out.getvalue())
    assert loaded["landmarks"][0]["id"] == 2
    assert loaded["landmarks"][0]["name"] == "Lab"
    assert loaded["landmarks"][0]["x"] == 1.25
