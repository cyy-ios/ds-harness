"""CLI entry: mini-harness run subcommand with optional --config."""
import argparse
import sys
from pathlib import Path
from typing import Optional

from mini_harness.dag import run_pipeline
from mini_harness.config import load_config


def _repo_root() -> Path:
    """Derive repo root: directory containing pyproject.toml."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent,
    ]
    for c in candidates:
        if (c / "pyproject.toml").exists():
            return c
    return Path.cwd()


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mini-harness",
        description="Minimal data processing harness — extract -> clean -> report",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Execute data processing pipeline")
    run_parser.add_argument(
        "sources", nargs="*", type=Path,
        help="One or more CSV / JSONL source files (falls back to config)",
    )
    run_parser.add_argument(
        "--config", "-c", type=Path, default=None,
        help="Path to JSON or YAML config file (auto-discovered if omitted)",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        root = _repo_root()
        cfg = load_config(root, explicit_path=args.config)

        # resolve sources: CLI args > config.sources
        if args.sources:
            source_paths = args.sources
        elif cfg.get("sources"):
            source_paths = [Path(s) for s in cfg["sources"]]
        else:
            print("Error: no sources provided (CLI args or config)", file=sys.stderr)
            sys.exit(1)

        run_pipeline(source_paths, root, cfg)


if __name__ == "__main__":
    main()
