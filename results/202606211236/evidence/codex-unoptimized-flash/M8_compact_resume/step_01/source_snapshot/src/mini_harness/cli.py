"""CLI for the mini data harness."""

from __future__ import annotations

import argparse
import json
import sys

from .runner import HarnessError, run_dag


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini_harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run the extract-clean-report DAG")
    run_parser.add_argument("sources", nargs="*", help="CSV or JSONL source files")
    run_parser.add_argument("--output", help="report JSON output path")
    run_parser.add_argument("--config", help="JSON or YAML config path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            from .config import resolve_run_settings

            sources, output, _config_path = resolve_run_settings(
                args.sources,
                args.output,
                args.config,
            )
            report = run_dag(sources, output)
        except HarnessError as exc:
            print(f"mini_harness: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "output": output,
                    "processed_count": report["processed_count"],
                    "rejected_count": report["rejected_count"],
                    "retry_count": report["retry_count"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2
