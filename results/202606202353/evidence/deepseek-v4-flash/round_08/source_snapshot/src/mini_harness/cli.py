import argparse
import sys
from mini_harness.config import load_config

def main():
    parser = argparse.ArgumentParser(description="mini_harness CLI")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Run the full data pipeline")
    run_parser.add_argument("--config", "-c", help="Path to config file (JSON/YAML)")
    run_parser.add_argument("--input", "-i", nargs="*", help="Input file(s) (CSV or JSONL)")
    run_parser.add_argument("--output", "-o", help="Output report path")
    run_parser.add_argument("files", nargs="*", help="Input files (positional)")
    args = parser.parse_args()
    if args.command == "run":
        from mini_harness.runner import run_dag
        # load config if provided
        config = {}
        if args.config:
            config = load_config(args.config)
        # resolve input files: positional > --input > config
        input_files = args.files if args.files else args.input if args.input else config.get("input")
        if not input_files:
            print("Error: input files are required (via positional, --input, or config)", file=sys.stderr)
            sys.exit(1)
        if isinstance(input_files, str):
            input_files = [input_files]
        # resolve output: CLI > config > default
        output_path = args.output or config.get("output", "report.json")
        result = run_dag(input_files)
        import json
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Report written to {output_path}")

if __name__ == "__main__":
    main()
