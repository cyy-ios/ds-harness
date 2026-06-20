"""report stage: generate structured report output to file and stdout."""
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from mini_harness.retry import with_retry


@with_retry(stage="report")
def generate_report(
    cleaned: List[dict[str, Any]],
    rejects: List[dict[str, Any]],
    source_files: List[str],
    retry_count: int,
    repo_root: Path,
    output_dir: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Generate structured report; write to file and emit summary to stdout."""
    reason_counts: Dict[str, int] = dict(
        Counter(r.get("_reject_reason", "unknown") for r in rejects)
    )

    per_source: Dict[str, Dict[str, int]] = {}
    for src in source_files:
        per_source[Path(src).name] = {"cleaned": 0, "rejected": 0, "total_records": 0}
    for _ in cleaned:
        _bump_per_source(per_source, "cleaned")
    for _ in rejects:
        _bump_per_source(per_source, "rejected")
    for v in per_source.values():
        v["total_records"] = v["cleaned"] + v["rejected"]

    report = {
        "summary": {
            "processed_count": len(cleaned),
            "rejected_count": len(rejects),
            "retry_count": retry_count,
            "source_files": source_files,
            "memory_summary_ref": str(repo_root / "memory" / "memory_summary.md"),
        },
        "details": {
            "reject_reasons": reason_counts,
            "per_source_files": per_source,
        },
    }

    out_root = Path(output_dir) if output_dir else (repo_root / "output")
    out_root.mkdir(parents=True, exist_ok=True)
    report_path = out_root / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    sys.stdout.write(json.dumps(report["summary"], ensure_ascii=False) + "\n")
    return report


def _bump_per_source(per_source: Dict[str, Dict[str, int]], key: str) -> None:
    """Increment key for first source bucket (best-effort without per-record source tracking)."""
    for name in per_source:
        per_source[name][key] += 1
        return
