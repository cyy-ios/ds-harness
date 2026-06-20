"""Base report generation module."""
from typing import List, Dict

def generate_report(processed_count: int, rejected_count: int, retry_count: int, source_files: List[str]) -> Dict:
    """Return the minimal report required by the harness specification."""
    return {
        "final_stats": {
            "processed_count": processed_count,
            "rejected_count": rejected_count,
            "retry_count": retry_count,
            "source_files": source_files
        }
    }
