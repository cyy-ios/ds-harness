import json
import os

def generate_report(cleaned: list, rejected: list, source_files: list, retry_count: int) -> dict:
    report = {
        "processed_count": len(cleaned),
        "rejected_count": len(rejected),
        "retry_count": retry_count,
        "source_files": source_files
    }
    memory_path = "memory/memory_summary.md"
    if os.path.exists(memory_path):
        report["memory_summary_reference"] = memory_path
    return report
