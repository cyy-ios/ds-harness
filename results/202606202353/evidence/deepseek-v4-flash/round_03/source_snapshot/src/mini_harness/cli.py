import argparse
import sys
from mini_harness.config import load_config

def main():
    parser = argparse.ArgumentParser(description="mini_harness CLI")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Run the full data pipeline")
    run_parser.add_argument("--config", "-c", help="Path to config file (JSON/YAML)")
    run_parser.add_argument("--input", "-i", help="Input file (CSV or JSONL)")
    run_parser.add_argument("--output", "-o", help="Output report path")
    args = parser.parse_args()
    if args.command == "run":
        from mini_harness.engine import run_pipeline
        # load config if provided
        config = {}
        if args.config:
            config = load_config(args.config)
        # resolve input
        input_path = args.input or config.get("input")
        if not input_path:
            print("Error: --input is required (directly or via config)", file=sys.stderr)
            sys.exit(1)
        # resolve output: CLI > config > default
        output_path = args.output or config.get("output", "report.json")
        run_pipeline(input_path, output_path)

if __name__ == "__main__":
    main()
