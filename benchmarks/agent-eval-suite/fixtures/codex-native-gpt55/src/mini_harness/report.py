"""Report helpers for the mini data harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


def build_report(
    records: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    retry_count: int,
    source_files: Iterable[str | Path],
) -> dict[str, Any]:
    return {
        "processed_count": len(records),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": [str(path) for path in source_files],
    }
