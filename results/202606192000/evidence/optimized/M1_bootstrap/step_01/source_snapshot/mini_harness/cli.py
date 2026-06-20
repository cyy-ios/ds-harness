"""CLI 入口：mini-harness run 子命令。"""
import argparse
import sys
from pathlib import Path

from mini_harness.dag import run_pipeline


def _repo_root() -> Path:
    """推导 repo root：pyproject.toml 所在目录。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent,
    ]
    for c in candidates:
        if (c / "pyproject.toml").exists():
            return c
    return Path.cwd()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mini-harness",
        description="最小数据处理流水线夹具 — extract → clean → report",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="执行数据处理流水线")
    run_parser.add_argument(
        "sources", nargs="+", type=Path,
        help="一个或多个 CSV / JSONL 源文件",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        root = _repo_root()
        run_pipeline(args.sources, root)


if __name__ == "__main__":
    main()
