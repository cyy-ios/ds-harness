"""CLI for the mini harness."""

from __future__ import annotations

import argparse
import json
import sys

from .config import load_config
from .runner import HarnessError, run_dag


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini_harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run the data harness DAG")
    run_parser.add_argument("sources", nargs="*", help="CSV or JSONL input files")
    run_parser.add_argument(
        "--output",
        required=False,
        help="report JSON path, resolved relative to the repository root",
    )
    run_parser.add_argument(
        "--config",
        help="optional JSON/YAML config path; defaults to harness.json/yaml/yml when present",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            report = run_dag(args.sources, output=args.output, config=args.config)
        except HarnessError as exc:
            print(f"mini_harness: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2
