import json
from pathlib import Path
from typing import List, Dict, Any


def generate_report(processed: int, rejected: int, retry_count: int, source_files: List[str]) -> Dict[str, Any]:
    """Generate a standard report dictionary."""
    return {
        "processed_count": processed,
        "rejected_count": rejected,
        "retry_count": retry_count,
        "source_files": source_files
    }


def generate_review_report(report: Dict[str, Any], memory_path: str = "memory/memory_summary.md") -> str:
    """Generate a human-readable review report that references memory_summary.md."""
    mem_path = Path(memory_path)
    memory_summary = ""
    if mem_path.exists():
        with open(mem_path, "r", encoding="utf-8") as f:
            memory_summary = f.read()

    lines = []
    lines.append("=== Data Harness Review Report ===")
    lines.append(f"Processed count: {report['processed_count']}")
    lines.append(f"Rejected count: {report['rejected_count']}")
    lines.append(f"Retry count: {report['retry_count']}")
    lines.append(f"Source files: {', '.join(report['source_files'])}")
    lines.append("")
    lines.append("--- Memory Summary (from memory/memory_summary.md) ---")
    lines.append(memory_summary if memory_summary else "(memory file not found)")
    lines.append("--- End of Report ---")
    return "\n".join(lines)
