"""Report construction for the mini harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MEMORY_SUMMARY = "memory/memory_summary.md"


def build_report(
    *,
    processed_records: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    retry_count: int,
    source_files: list[str],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "processed_count": len(processed_records),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files,
        "logs": logs,
        "records": processed_records,
        "rejects": rejects,
        "memory_summary": MEMORY_SUMMARY,
    }


def write_report(output_path: Path, report: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
