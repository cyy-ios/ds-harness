import json
from pathlib import Path
from typing import List, Dict
from mini_harness.repo import get_repo_root

def load_memory_summary() -> str:
    repo_root = get_repo_root()
    path = Path(repo_root) / "memory" / "memory_summary.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def load_compatibility_notes() -> str:
    repo_root = get_repo_root()
    path = Path(repo_root) / "docs" / "compatibility-notes.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def load_performance_baseline() -> dict:
    repo_root = get_repo_root()
    path = Path(repo_root) / "benchmarks" / "perf-baseline.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def generate_review_report(processed_count: int, rejected_count: int, retry_count: int, source_files: List[str]) -> dict:
    """Generate a memory-aware review report with design decisions and final stats."""
    memory_summary = load_memory_summary()
    compatibility_notes = load_compatibility_notes()
    performance_baseline = load_performance_baseline()
    
    review = {
        "final_stats": {
            "processed_count": processed_count,
            "rejected_count": rejected_count,
            "retry_count": retry_count,
            "source_files": source_files
        },
        "memory_document": {
            "memory_summary": memory_summary,
            "compatibility_notes": compatibility_notes
        },
        "performance_baseline": performance_baseline
    }
    return review
