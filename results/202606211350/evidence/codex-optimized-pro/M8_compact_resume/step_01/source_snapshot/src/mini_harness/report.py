"""Report generation for mini_harness.

Produces the structured JSON report required by the stable contract:
processed_count, rejected_count, retry_count, source_files.
"""

import json
from pathlib import Path

from mini_harness.config import REPO_ROOT


def _resolve_repo_path(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def generate_report(
    clean: list[dict],
    rejects: list[dict],
    retry_count: int,
    source_files: list[str],
    output_path: str,
) -> dict:
    """Produce and write the JSON report to *output_path*.

    Returns the report dict.
    """
    report = {
        "processed_count": len(clean),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files,
    }
    out_path = _resolve_repo_path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def read_report(report_path: str) -> dict:
    """Read and return a previously written report JSON file."""
    rp = _resolve_repo_path(report_path)
    if not rp.is_file():
        raise FileNotFoundError(f"report not found: {rp}")
    return json.loads(rp.read_text(encoding="utf-8"))


__all__ = ["generate_report", "read_report"]
