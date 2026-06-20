import os
import json
import tempfile
import shutil
from mini_harness.pipeline import run_pipeline

def test_report_includes_memory_summary():
    """Ensure report.json contains memory_summary when memory file exists."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    memory_path = os.path.join(repo_root, "memory", "memory_summary.md")
    output_dir = tempfile.mkdtemp()
    try:
        # Use an input file that exists, e.g., test_input.csv in repo root
        input_file = os.path.join(repo_root, "test_input.csv")
        stats, logs = run_pipeline([input_file], output_dir, memory_path)
        report_path = os.path.join(output_dir, "report.json")
        assert os.path.exists(report_path)
        with open(report_path, "r") as f:
            report = json.load(f)
        assert "memory_summary" in report
        with open(memory_path, "r") as f:
            expected = f.read().strip()
        assert report["memory_summary"] == expected
        # Check some stats
        assert report["processed_count"] == stats["processed_count"]
        assert report["rejected_count"] == stats["rejected_count"]
        assert report["retry_count"] == stats["retry_count"]
    finally:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
