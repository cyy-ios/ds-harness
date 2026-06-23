"""Report construction and persistence for the mini data harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_report(
    cleaned: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    retry_count: int,
    source_files: list[str],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the stable JSON report payload."""

    return {
        "processed_count": len(cleaned),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files,
        "records": cleaned,
        "rejects": rejects,
        "logs": logs,
        "memory_reference": "memory/memory_summary.md",
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    """Write a report as deterministic UTF-8 JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
