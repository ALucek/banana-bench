"""
Standalone CLI for generating visualizers from existing results.

Usage:
    python -m src.visualize results/game.json
    python -m src.visualize results/game.json --output visualizer.html
"""

import argparse
import sys
from pathlib import Path

from .visualizer import generate_visualizer


def main():
    parser = argparse.ArgumentParser(
        description="Generate an HTML visualizer from Banana-Bench results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.visualize results/game.json
  python -m src.visualize results/game.json --output my_visualizer.html
  python -m src.visualize results/game.json && open results/game.html
        """
    )
    parser.add_argument(
        "results",
        help="Path to the results JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for HTML file (default: same as input with .html extension)"
    )

    args = parser.parse_args()

    # Validate input file
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Error: Results file not found: {args.results}", file=sys.stderr)
        sys.exit(1)

    if not results_path.suffix == ".json":
        print("Warning: Input file doesn't have .json extension", file=sys.stderr)

    # Generate visualizer
    try:
        output_path = generate_visualizer(
            results_path,
            args.output
        )
        print(f"Visualizer generated: {output_path}")
        print(f"Open in browser: open {output_path}")
    except Exception as e:
        print(f"Error generating visualizer: {e}", file=sys.stderr)
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
