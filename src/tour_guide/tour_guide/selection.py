"""Interactive landmark selection.

Presents the landmark map as a numbered menu and lets the operator pick a tour
route as an ordered list of landmarks. Pure Python, no ROS dependency, so this
module can be run standalone for development and demo.
"""

import argparse
import sys
from typing import List, Optional

from tour_guide.landmark_map import Landmark, load_landmarks


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
    """Parse a comma-separated selection like '0,2,1' into menu indices.

    Raises ValueError on bad input.
    """
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


def select_tour(
    landmarks: List[Landmark],
    input_fn=input,
    output_fn=print,
) -> List[Landmark]:
    """Run the interactive selection loop and return the chosen tour route.

    `input_fn` and `output_fn` are injectable so this can be tested without
    a real terminal.
    """
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
        output_fn("\nPlanned tour:")
        for step, lm in enumerate(chosen, start=1):
            output_fn(f"  {step}. {lm.display_name}  (x={lm.x:.2f}, y={lm.y:.2f})")

        confirm = input_fn("Confirm? [y/N]: ").strip().lower()
        if confirm in ("y", "yes"):
            return chosen
        output_fn("Cancelled. Re-select.\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive tour route selection.")
    parser.add_argument(
        "landmarks_file",
        help="Path to the landmark map YAML file",
    )
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
