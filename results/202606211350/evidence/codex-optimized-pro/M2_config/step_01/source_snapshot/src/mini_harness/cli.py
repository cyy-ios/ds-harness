"""CLI for mini_harness - uses argparse, supports ``run`` subcommand."""

import argparse
import json
import sys

from mini_harness.runner import HarnessError, run_dag


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mini_harness",
        description="Mini data processing harness",
    )
    sub = parser.add_subparsers(dest="command")

    # --- run ----------------------------------------------------------------
    run_parser = sub.add_parser("run", help="Execute the DAG pipeline")
    run_parser.add_argument(
        "sources", nargs="+",
        help="One or more CSV / JSONL source files",
    )
    run_parser.add_argument(
        "--output", "-o", required=True,
        help="Report output path (e.g. tmp/report.json)",
    )
    run_parser.add_argument(
        "--config", "-c", default=None,
        help="Optional JSON/YAML config path; built-in defaults used otherwise",
    )

    args = parser.parse_args(argv)
    if args.command != "run":
        parser.print_help()
        sys.exit(1)

    try:
        report = run_dag(
            source_files=args.sources,
            output=args.output,
            config_path=args.config,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
    except HarnessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
