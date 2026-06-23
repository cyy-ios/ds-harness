import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="mini_harness CLI")
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run", help="Run the full data pipeline")
    run_parser.add_argument("--input", "-i", required=True, help="Input file (CSV or JSONL)")
    run_parser.add_argument("--output", "-o", default="report.json", help="Output report path")
    args = parser.parse_args()
    if args.command == "run":
        from mini_harness.engine import run_pipeline
        run_pipeline(args.input, args.output)

if __name__ == "__main__":
    main()
