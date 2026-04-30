"""Interactive landmark selection.

Presents the landmark map as a numbered menu, lets the operator pick a tour
route, and optionally reorders it to minimize total travel distance. Pure
Python with no ROS dependency, so this module can be exercised standalone in
unit tests and in an offline CLI for development and demos.
"""

import argparse
import math
import sys
from itertools import permutations
from typing import List, Optional, Tuple

from tour_guide.landmark_map import Landmark, load_landmarks


_BRUTE_FORCE_LIMIT = 8  # 8! = 40320 permutations -- still milliseconds


def format_menu(landmarks: List[Landmark]) -> str:
    if not landmarks:
        return "  (no landmarks found)\n"
    lines = []
    for idx, lm in enumerate(landmarks):
        lines.append(
            f"  [{idx}] {lm.display_name}  "
            f"(id={lm.id}, x={lm.x:.2f}, y={lm.y:.2f}, yaw={lm.yaw:.2f})"
        )
    return "\n".join(lines) + "\n"


def parse_selection(raw: str, n_landmarks: int) -> List[int]:
    """Parse a comma-separated selection like '0,2,1' into menu indices."""
    if not raw.strip():
        raise ValueError("empty selection")

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        raise ValueError("empty selection")

    indices = []
    for tok in tokens:
        try:
            i = int(tok)
        except ValueError:
            raise ValueError(f"not a number: {tok!r}")
        if i < 0 or i >= n_landmarks:
            raise ValueError(f"out of range: {i} (valid range 0..{n_landmarks - 1})")
        indices.append(i)
    return indices


def route_length(route: List[Landmark], start: Tuple[float, float] = (0.0, 0.0)) -> float:
    """Total Euclidean travel distance: start -> route[0] -> route[1] -> ..."""
    if not route:
        return 0.0
    total = math.hypot(route[0].x - start[0], route[0].y - start[1])
    for a, b in zip(route, route[1:]):
        total += math.hypot(b.x - a.x, b.y - a.y)
    return total


def optimize_route(route: List[Landmark],
                   start: Tuple[float, float] = (0.0, 0.0)) -> List[Landmark]:
    """Reorder a chosen set of landmarks to minimize total travel distance.

    Brute force for small routes (optimal); nearest-neighbor heuristic above
    `_BRUTE_FORCE_LIMIT` (close to optimal for the small N we care about).
    """
    if len(route) <= 2:
        return list(route)

    if len(route) <= _BRUTE_FORCE_LIMIT:
        best = min(permutations(route), key=lambda p: route_length(list(p), start))
        return list(best)

    # Greedy nearest-neighbor fallback
    remaining = list(route)
    cur = start
    ordered: List[Landmark] = []
    while remaining:
        nxt = min(remaining, key=lambda lm: math.hypot(lm.x - cur[0], lm.y - cur[1]))
        ordered.append(nxt)
        remaining.remove(nxt)
        cur = (nxt.x, nxt.y)
    return ordered


def select_tour(
    landmarks: List[Landmark],
    input_fn=input,
    output_fn=print,
    start: Tuple[float, float] = (0.0, 0.0),
) -> List[Landmark]:
    """Run the interactive selection loop and return the chosen tour route."""
    if not landmarks:
        output_fn("No landmarks available. Run a sweep first.")
        return []

    output_fn("Available landmarks:")
    output_fn(format_menu(landmarks))

    while True:
        output_fn(
            "Enter the tour as a comma-separated list of menu numbers "
            "(e.g. '0,2,1'), or 'q' to quit:"
        )
        raw = input_fn("> ").strip()

        if raw.lower() in ("q", "quit", "exit"):
            return []

        try:
            indices = parse_selection(raw, len(landmarks))
        except ValueError as e:
            output_fn(f"Invalid selection: {e}. Try again.")
            continue

        chosen = [landmarks[i] for i in indices]
        original_len = route_length(chosen, start)
        optimized = optimize_route(chosen, start)
        optimized_len = route_length(optimized, start)

        savings = original_len - optimized_len
        output_fn(f"\nYour order: total travel ~{original_len:.2f} m")
        for step, lm in enumerate(chosen, start=1):
            output_fn(f"  {step}. {lm.display_name}  (x={lm.x:.2f}, y={lm.y:.2f})")
        output_fn(f"\nOptimized order: total travel ~{optimized_len:.2f} m"
                  f"  (saves {savings:.2f} m)")
        for step, lm in enumerate(optimized, start=1):
            output_fn(f"  {step}. {lm.display_name}  (x={lm.x:.2f}, y={lm.y:.2f})")

        prompt = "Use [o]ptimized order, [k]eep your order, or [r]eselect? "
        choice = input_fn(prompt).strip().lower()
        if choice in ("o", "opt", "optimize"):
            return optimized
        if choice in ("k", "keep"):
            return chosen
        output_fn("Cancelled. Re-select.\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive tour route selection.")
    parser.add_argument("landmarks_file", help="Path to the landmark map YAML file")
    args = parser.parse_args(argv)

    try:
        landmarks = load_landmarks(args.landmarks_file)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    tour = select_tour(landmarks)
    if not tour:
        print("No tour selected.")
        return 0

    print("\nFinal tour route:")
    for step, lm in enumerate(tour, start=1):
        print(f"  {step}. id={lm.id} name={lm.display_name} x={lm.x} y={lm.y} yaw={lm.yaw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
