"""CLI with argparse."""

import argparse
import sys
from pathlib import Path
from mini_harness.pipeline import run_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def cmd_run(args):
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = REPO_ROOT / input_path
    run_pipeline(input_path=str(input_path), repo_root=str(REPO_ROOT))
    print("Pipeline complete. See evidence/ for report.")


def main():
    parser = argparse.ArgumentParser(prog="mini_harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the data processing pipeline")
    p_run.add_argument("--input", required=True, help="Input file path (CSV or JSONL)")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
