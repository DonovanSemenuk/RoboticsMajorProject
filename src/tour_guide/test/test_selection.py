"""Tests for landmark selection and route optimization.

Pure-Python tests that don't require ROS or a running robot. Run with:
    pytest src/tour_guide/test/test_selection.py
"""

import math

import pytest

from tour_guide.landmark_map import Landmark, load_landmarks, save_landmarks
from tour_guide.selection import (
    format_menu,
    optimize_route,
    parse_selection,
    route_length,
    select_tour,
)


def make_landmarks():
    return [
        Landmark(id=0, x=1.0, y=2.0, yaw=0.0, name="Front Desk"),
        Landmark(id=1, x=-0.5, y=0.0, yaw=1.57, name="Gift Shop"),
        Landmark(id=2, x=3.0, y=-1.0, yaw=0.0),
    ]


# ---- parse_selection -------------------------------------------------------

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


# ---- format_menu -----------------------------------------------------------

def test_format_menu_named_and_unnamed():
    menu = format_menu(make_landmarks())
    assert "[0] Front Desk" in menu
    assert "[1] Gift Shop" in menu
    assert "[2] Marker 2" in menu


def test_format_menu_empty():
    assert "no landmarks" in format_menu([])


# ---- route_length / optimize_route -----------------------------------------

def test_route_length_empty():
    assert route_length([]) == 0.0


def test_route_length_single_from_origin():
    lm = Landmark(id=0, x=3.0, y=4.0, yaw=0.0)
    assert route_length([lm], start=(0.0, 0.0)) == pytest.approx(5.0)


def test_route_length_chain():
    lms = [
        Landmark(id=0, x=1.0, y=0.0, yaw=0.0),
        Landmark(id=1, x=1.0, y=1.0, yaw=0.0),
        Landmark(id=2, x=2.0, y=1.0, yaw=0.0),
    ]
    # 0->lm0: 1, lm0->lm1: 1, lm1->lm2: 1 = 3
    assert route_length(lms, start=(0.0, 0.0)) == pytest.approx(3.0)


def test_optimize_route_short_circuits_on_two_or_fewer():
    lms = make_landmarks()[:2]
    assert optimize_route(lms) == lms


def test_optimize_route_picks_shortest_order_brute_force():
    # A pathological input: walking 0,1,2 in given order doubles back.
    lms = [
        Landmark(id=0, x=5.0, y=0.0, yaw=0.0),
        Landmark(id=1, x=1.0, y=0.0, yaw=0.0),
        Landmark(id=2, x=3.0, y=0.0, yaw=0.0),
    ]
    optimized = optimize_route(lms, start=(0.0, 0.0))
    assert [lm.id for lm in optimized] == [1, 2, 0]
    # And the new total is shorter than the worst.
    assert route_length(optimized, (0.0, 0.0)) < route_length(lms, (0.0, 0.0))


def test_optimize_route_falls_back_to_nearest_neighbor_for_large_input():
    # Bigger than _BRUTE_FORCE_LIMIT (8) -- exercise the heuristic branch.
    lms = [Landmark(id=i, x=float(i), y=0.0, yaw=0.0) for i in range(10)]
    optimized = optimize_route(lms, start=(0.0, 0.0))
    # Nearest-neighbor from origin should walk left-to-right.
    assert [lm.id for lm in optimized] == list(range(10))


# ---- select_tour interactive flow ------------------------------------------

def test_select_tour_keep_user_order():
    inputs = iter(["2,0,1", "k"])
    outputs = []
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=outputs.append,
    )
    assert [lm.id for lm in tour] == [2, 0, 1]


def test_select_tour_use_optimized_order():
    inputs = iter(["0,1,2", "o"])
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=lambda _msg: None,
        start=(0.0, 0.0),
    )
    expected = optimize_route(make_landmarks(), start=(0.0, 0.0))
    assert [lm.id for lm in tour] == [lm.id for lm in expected]


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
    inputs = iter(["bogus", "5,5,5", "0,1", "k"])
    msgs = []
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=msgs.append,
    )
    assert [lm.id for lm in tour] == [0, 1]
    assert any("Invalid" in m for m in msgs)


def test_select_tour_reselect_then_keep():
    inputs = iter(["0,1", "r", "2", "k"])
    tour = select_tour(
        make_landmarks(),
        input_fn=lambda _prompt="": next(inputs),
        output_fn=lambda _msg: None,
    )
    assert [lm.id for lm in tour] == [2]


# ---- landmark_map I/O ------------------------------------------------------

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
