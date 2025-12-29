"""
Main entry point for running Banana-Bench benchmarks.

Usage:
    python -m src.main config.yaml
    python -m src.main config.yaml --output results/run1.json --verbose
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

from .environment import BananaBench, BenchmarkConfig


def load_config(config_path: str) -> BenchmarkConfig:
    """Load benchmark configuration from a YAML file."""
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    return BenchmarkConfig(**data)


def main():
    parser = argparse.ArgumentParser(
        description="Run a Banana-Bench benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example config.yaml:
  num_players: 1
  max_turns: 50
  seed: 42
  models:
    - gpt-4o
  temperature: 0.7
  max_tokens: 2048
        """
    )
    parser.add_argument(
        "config",
        nargs="?",
        help="Path to YAML configuration file (not needed with --resume)"
    )
    parser.add_argument(
        "--resume",
        help="Resume from a saved result JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to save results JSON (default: results/<timestamp>.json)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress to stdout"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate an HTML visualizer after the benchmark"
    )

    args = parser.parse_args()

    # Handle resume mode
    if args.resume:
        if args.verbose:
            print(f"Resuming from: {args.resume}")
        try:
            bench = BananaBench.resume(args.resume)
            if args.verbose:
                print(f"Loaded state: Turn {bench.current_turn}, {bench.game.tiles_remaining} tiles in bunch")
                print()
        except Exception as e:
            print(f"Error resuming from {args.resume}: {e}", file=sys.stderr)
            sys.exit(1)

        # Determine output path for resumed run
        if args.output:
            output_path = Path(args.output)
        else:
            # Default: add _resumed to original filename
            resume_path = Path(args.resume)
            output_path = resume_path.parent / f"{resume_path.stem}_resumed{resume_path.suffix}"

    else:
        # Normal mode: load config and create new benchmark
        if not args.config:
            print("Error: config file required (or use --resume)", file=sys.stderr)
            sys.exit(1)

        try:
            config = load_config(args.config)
        except Exception as e:
            print(f"Error loading config: {e}", file=sys.stderr)
            sys.exit(1)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path("results") / f"benchmark_{timestamp}.json"

        # Create benchmark
        bench = BananaBench.create(config=config)

        if args.verbose:
            print(f"Config: {args.config}")
            print(f"Output: {output_path}")
            print()
    
    try:
        result = bench.run(verbose=args.verbose)
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        result = bench.get_result()
        bench.end_reason = "Interrupted by user"
    except Exception as e:
        print(f"Error during benchmark: {e}", file=sys.stderr)
        result = bench.get_result()
        bench.end_reason = f"Error: {str(e)}"
    
    # Save results
    bench.save_result(output_path)

    if args.verbose:
        print()
        print(f"Results saved to: {output_path}")

    # Generate visualizer if requested
    if args.visualize:
        from .visualizer import generate_visualizer
        html_path = generate_visualizer(output_path)
        print(f"Visualizer generated: {html_path}")
    
    # Print summary
    print()
    print("=== Benchmark Summary ===")
    print(f"Total turns: {result.total_turns}")
    print(f"End reason: {result.end_reason}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    if result.winner:
        print(f"Winner: {result.winner}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

