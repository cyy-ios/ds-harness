"""Tests for the report module."""

import json
import tempfile
import os
from pathlib import Path

from mini_harness.report import build_report, write_report, load_memory_summary


def test_build_report_minimal():
    report = build_report(
        processed_count=4,
        rejected_count=2,
        retry_count=0,
        source_files=["data/input.csv", "data/events.jsonl"],
    )
    assert report["pipeline"] == "mini_harness"
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv", "data/events.jsonl"]
    assert "generated_at" in report
    assert "stages" in report
    # Without memory_ref, key should be absent
    assert "memory_reference" not in report


def test_build_report_with_memory_ref():
    report = build_report(
        processed_count=4,
        rejected_count=2,
        retry_count=1,
        source_files=["data/input.csv"],
        memory_ref="memory/memory_summary.md",
    )
    assert report["memory_reference"] == "memory/memory_summary.md"


def test_write_report():
    report = build_report(
        processed_count=1,
        rejected_count=0,
        retry_count=0,
        source_files=["test.csv"],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.json")
        write_report(report, out)
        assert os.path.isfile(out)
        with open(out, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["processed_count"] == 1
        assert loaded["pipeline"] == "mini_harness"


def test_load_memory_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        mem_file = os.path.join(tmpdir, "memory_summary.md")
        Path(mem_file).write_text("# Test Memory", encoding="utf-8")
        content = load_memory_summary(mem_file)
        assert content == "# Test Memory"


def test_load_memory_summary_missing():
    content = load_memory_summary("/nonexistent/path.md")
    assert content is None


def test_report_structure_matches_expected():
    """Verify the report matches the acceptance contract."""
    report = build_report(
        processed_count=4,
        rejected_count=2,
        retry_count=0,
        source_files=["data/input.csv", "data/events.jsonl"],
    )
    assert set(report.keys()) >= {
        "pipeline", "generated_at", "processed_count", "rejected_count",
        "retry_count", "source_files", "stages",
    }
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv", "data/events.jsonl"]
