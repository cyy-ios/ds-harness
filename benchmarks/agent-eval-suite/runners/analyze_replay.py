#!/usr/bin/env python3
"""Extract deterministic tool-event metadata for agent-reviewed scoring."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def iter_records(path: Path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            yield line


def collect(paths: list[Path]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "records": 0,
        "assistant_tool_calls": 0,
        "tool_results": 0,
        "finish_count": 0,
        "tool_counts": {},
    }
    for path in paths:
        for record in iter_records(path):
            metadata["records"] += 1
            if not isinstance(record, dict):
                continue
            if record.get("kind") == "tool_call":
                metadata["assistant_tool_calls"] += 1
                tool = str(record.get("tool", "unknown"))
                metadata["tool_counts"][tool] = metadata["tool_counts"].get(tool, 0) + 1
                if tool == "finish":
                    metadata["finish_count"] += 1
            if record.get("kind") == "tool_result":
                metadata["tool_results"] += 1
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    report = {"metadata": collect([Path(p) for p in args.paths])}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
