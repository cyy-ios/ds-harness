"""report stage: generate JSON report with required fields."""
import json
import sys
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
    **kwargs: Any,
) -> Dict[str, Any]:
    """Generate JSON report referencing memory/memory_summary.md."""
    report = {
        "processed_count": len(cleaned),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files,
        "memory_summary_ref": str(repo_root / "memory" / "memory_summary.md"),
    }
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report
