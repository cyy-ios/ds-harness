"""CLI with argparse."""

import argparse
import sys
from pathlib import Path
from mini_harness.pipeline import run_pipeline
from mini_harness.config import load_config, find_default_config

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_config(config_path, repo_root):
    """Load config from explicit path or auto-discover default."""
    if config_path:
        return load_config(config_path, repo_root)
    default = find_default_config(repo_root)
    if default:
        return load_config(default, repo_root)
    return {}


def cmd_run(args):
    config = _resolve_config(args.config, str(REPO_ROOT))

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = REPO_ROOT / input_path

    max_retries = args.max_retries
    if max_retries is None:
        max_retries = config.get("max_retries")

    run_pipeline(
        input_path=str(input_path),
        repo_root=str(REPO_ROOT),
        max_retries=max_retries,
    )
    print("Pipeline complete. See evidence/ for report.")


def main():
    parser = argparse.ArgumentParser(prog="mini_harness")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the data processing pipeline")
    p_run.add_argument("--input", required=True, help="Input file path (CSV or JSONL)")
    p_run.add_argument(
        "--config",
        default=None,
        help="Path to config file (JSON or YAML). Auto-discovered if omitted.",
    )
    p_run.add_argument(
        "--max-retries", type=int, default=None, help="Max retry attempts per stage"
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
