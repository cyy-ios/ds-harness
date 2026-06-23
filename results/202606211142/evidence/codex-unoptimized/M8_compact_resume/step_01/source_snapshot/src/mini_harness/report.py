"""Report building and writing helpers for mini_harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STAGES = ("extract", "clean", "report")


def build_report(state: dict[str, Any]) -> dict[str, Any]:
    root = state["root"]
    output = state["output"]
    return {
        "processed_count": len(state.get("cleaned_records", [])),
        "rejected_count": len(state.get("rejects", [])),
        "retry_count": state["retry_count"],
        "output": display_path(root, output),
        "source_files": [display_path(root, source) for source in state["sources"]],
        "records": state.get("cleaned_records", []),
        "rejects": state.get("rejects", []),
        "stages": list(STAGES),
        "logs": state["logs"],
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def display_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()
