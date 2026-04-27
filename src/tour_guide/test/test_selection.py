"""Tests for landmark selection logic.

Pure-Python tests that don't require ROS or a running robot. Run with:
    pytest src/tour_guide/test/test_selection.py
"""

import pytest

from tour_guide.landmark_map import Landmark, load_landmarks, save_landmarks
from tour_guide.selection import format_menu, parse_selection, select_tour


def make_landmarks():
    return [
        Landmark(id=0, x=1.0, y=2.0, yaw=0.0, name="Front Desk"),
        Landmark(id=1, x=-0.5, y=0.0, yaw=1.57, name="Gift Shop"),
        Landmark(id=2, x=3.0, y=-1.0, yaw=0.0),
    ]


def test_parse_selection_basic():
    assert parse_selection("0,2,1", 3) == [0, 2, 1]


def test_parse_selection_with_spaces():
    assert parse_selection(" 0 , 1 , 2 ", 3) == [0, 1, 2]


def test_parse_selection_single():
    assert parse_selection("1", 3) == [1]


def test_parse_selection_repeats_allowed():
    assert parse_selection("0,0,1", 3) == [0, 0, 1]


def test_parse_selection_rejects_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        parse_selection("0,5", 3)


def test_parse_selection_rejects_negative():
    with pytest.raises(ValueError, match="out of range"):
        parse_selection("-1", 3)


def test_parse_selection_rejects_non_numeric():
    with pytest.raises(ValueError, match="not a number"):
        parse_selection("0,foo", 3)


def test_parse_selection_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        parse_selection("", 3)


def test_format_menu_named_and_unnamed():
    menu = format_menu(make_landmarks())
    assert "[0] Front Desk" in menu
    assert "[1] Gift Shop" in menu
    assert "[2] Marker 2" in menu


def test_format_menu_empty():
    assert "no landmarks" in format_menu([])


def test_select_tour_returns_chosen_in_order():
    inputs = iter(["2,0,1", "y"])
    outputs = []
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=outputs.append,
    )
    assert [lm.id for lm in tour] == [2, 0, 1]


def test_select_tour_quit():
    inputs = iter(["q"])
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=lambda _msg: None,
    )
    assert tour == []


def test_select_tour_empty_landmarks():
    msgs = []
    tour = select_tour(
        [],
        input_fn=lambda _prompt="": "",
        output_fn=msgs.append,
    )
    assert tour == []
    assert any("No landmarks" in m for m in msgs)


def test_select_tour_retries_after_bad_input():
    inputs = iter(["bogus", "5,5,5", "0,1", "y"])
    msgs = []
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=msgs.append,
    )
    assert [lm.id for lm in tour] == [0, 1]
    assert any("Invalid" in m for m in msgs)


def test_select_tour_cancel_then_reselect():
    inputs = iter(["0,1", "n", "2", "y"])
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=lambda _msg: None,
    )
    assert [lm.id for lm in tour] == [2]


def test_landmark_roundtrip(tmp_path):
    landmarks = make_landmarks()
    path = tmp_path / "landmarks.yaml"
    save_landmarks(str(path), landmarks)
    loaded = load_landmarks(str(path))
    assert loaded == landmarks


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_landmarks(str(tmp_path / "nonexistent.yaml"))


def test_load_real_locations_yaml():
    """Sanity-check that the committed landmarks/locations.yaml parses cleanly."""
    landmarks = load_landmarks("landmarks/locations.yaml")
    assert len(landmarks) == 4
    assert {lm.id for lm in landmarks} == {0, 1, 2, 3}
