"""Command line interface for mini_harness."""

from __future__ import annotations

import argparse
import json
from typing import Iterable

from .config import load_config, merge_config
from .runner import repo_root, resolve_from_root, run_dag, write_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini_harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run the mini data harness")
    run_parser.add_argument(
        "input_paths",
        nargs="*",
        help="CSV or JSONL input paths, resolved relative to the repo root",
    )
    run_parser.add_argument(
        "--config",
        help="JSON or simple YAML config path, resolved relative to the repo root",
    )
    run_parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="CSV or JSONL input path, resolved relative to the repo root",
    )
    run_parser.add_argument(
        "--output",
        help="report JSON path, resolved relative to the repo root",
    )
    run_parser.add_argument(
        "--rejects-output",
        help="rejects JSONL path, resolved relative to the repo root",
    )
    run_parser.add_argument(
        "--log-output",
        help="structured log JSONL path, resolved relative to the repo root",
    )
    run_parser.add_argument(
        "--max-retries",
        type=int,
        help="maximum retries per DAG stage",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "run":
        root = repo_root()
        cli_inputs = list(args.input_paths)
        if args.inputs:
            cli_inputs.extend(args.inputs)
        config = merge_config(
            load_config(args.config, root),
            inputs=cli_inputs or None,
            output=args.output,
            rejects_output=args.rejects_output,
            log_output=args.log_output,
            max_retries=args.max_retries,
        )
        input_paths = [resolve_from_root(path, root) for path in config.inputs]
        output_path = resolve_from_root(config.output, root)
        rejects_path = resolve_from_root(config.rejects_output, root)
        log_path = resolve_from_root(config.log_output, root)

        result = run_dag(input_paths, max_retries=config.max_retries, root=root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rejects_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(
            json.dumps(result.report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_jsonl(rejects_path, result.rejects)
        write_jsonl(log_path, result.logs)
        print(json.dumps(result.report, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2
