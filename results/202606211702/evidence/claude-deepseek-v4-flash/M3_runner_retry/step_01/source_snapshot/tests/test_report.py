"""Tests for ``mini_harness.report``."""

from mini_harness.report import build_report, MEMORY_REFERENCE


def test_build_report_counts():
    """build_report returns correct processed/rejected/retry counts."""
    result = build_report(
        cleaned=[{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}],
        rejects=[{"id": ""}, {"id": ""}],
        retry_count=0,
        source_files=["data/input.csv", "data/events.jsonl"],
    )
    assert result["processed_count"] == 4
    assert result["rejected_count"] == 2
    assert result["retry_count"] == 0
    assert result["source_files"] == ["data/input.csv", "data/events.jsonl"]
    assert result["memory_reference"] == "memory/memory_summary.md"


def test_build_report_empty():
    """build_report handles empty inputs."""
    result = build_report(
        cleaned=[],
        rejects=[],
        retry_count=2,
        source_files=[],
    )
    assert result["processed_count"] == 0
    assert result["rejected_count"] == 0
    assert result["retry_count"] == 2
    assert result["memory_reference"] == "memory/memory_summary.md"


def test_build_report_retry_count():
    """build_report preserves the retry_count value."""
    result = build_report(
        cleaned=[{"id": "x"}],
        rejects=[],
        retry_count=3,
        source_files=["data/single.csv"],
    )
    assert result["retry_count"] == 3


def test_memory_reference_constant():
    """MEMORY_REFERENCE is a non-empty string."""
    assert isinstance(MEMORY_REFERENCE, str)
    assert len(MEMORY_REFERENCE) > 0
    assert MEMORY_REFERENCE == "memory/memory_summary.md"


def test_build_report_source_files_abs():
    """build_report preserves absolute source file paths."""
    abs_paths = [
        "/home/user/data/input.csv",
        "/home/user/data/events.jsonl",
    ]
    result = build_report(
        cleaned=[{"id": "1"}],
        rejects=[],
        retry_count=0,
        source_files=abs_paths,
    )
    assert result["source_files"] == abs_paths
