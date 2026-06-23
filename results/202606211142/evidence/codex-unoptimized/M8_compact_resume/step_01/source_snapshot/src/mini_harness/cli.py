"""Command line interface for mini_harness."""

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
    run_parser.add_argument("sources", nargs="*", help="CSV or JSONL input files, relative to repo root")
    run_parser.add_argument("--output", help="report JSON path, relative to repo root")
    run_parser.add_argument("--config", help="JSON or YAML config path, relative to repo root")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "run":
        try:
            report = _run(args)
        except HarnessError as exc:
            print(f"mini_harness: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(_summary(report), ensure_ascii=False, sort_keys=True))
        return 0

    return 1


def _run(args: argparse.Namespace) -> dict[str, object]:
    config = load_config(run_dag.repo_root(), args.config)
    sources = args.sources or config.get("sources") or config.get("source_files")
    output = args.output or config.get("output") or "tmp/report.json"
    if not sources:
        raise HarnessError("run requires source files from CLI args or config")
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list) or not all(isinstance(source, str) for source in sources):
        raise HarnessError("config sources must be a string or list of strings")
    if not isinstance(output, str):
        raise HarnessError("config output must be a string")
    return run_dag(sources, output, config=config)


def _summary(report: dict[str, object]) -> dict[str, object]:
    return {
        "output": report.get("output"),
        "processed_count": report.get("processed_count", 0),
        "rejected_count": report.get("rejected_count", 0),
        "retry_count": report.get("retry_count", 0),
        "source_files": report.get("source_files", []),
    }
