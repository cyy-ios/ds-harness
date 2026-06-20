"""Report stage: write summary JSON and reference memory."""

import json
from pathlib import Path
from datetime import datetime, timezone


def write_report(processed_count, rejected_count, retry_count, source_files, repo_root):
    evidence_dir = Path(repo_root) / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processed_count": processed_count,
        "rejected_count": rejected_count,
        "retry_count": retry_count,
        "source_files": source_files,
        "memory_reference": "memory/memory_summary.md",
    }

    out_path = evidence_dir / "run_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return str(out_path)
