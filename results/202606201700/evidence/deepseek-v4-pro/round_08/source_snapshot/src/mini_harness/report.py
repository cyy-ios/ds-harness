from typing import Any, Dict, List, Optional


def generate_report(
    cleaned: List[Dict[str, Any]],
    rejects: List[Dict[str, Any]],
    retry_count: int,
    source_files: List[str],
    memory_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a structured report.

    Parameters:
        cleaned: successfully processed records.
        rejects: records rejected during cleaning.
        retry_count: total retry attempts across all stages.
        source_files: list of input file paths.
        memory_path: optional path to memory_summary.md; if present, the first
            200 characters are included as ``memory_reference``.
    """
    report: Dict[str, Any] = {
        "processed_count": len(cleaned),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files,
    }
    if memory_path:
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                report["memory_reference"] = f.read(200)
        except FileNotFoundError:
            pass
    return report
