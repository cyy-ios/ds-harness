"""Tests for the report module."""
import json
import sys
from pathlib import Path

REPO = Path(r"C:\项目\ds-harness\tmp\agent-eval-fixture-20260621230522")
sys.path.insert(0, str(REPO))

from mini_harness.report import build_report, write_report, validate_report


def test_build_report_basic():
    report = build_report(
        [{"id": "1"}, {"id": "2"}],
        [{"no_id": True}],
        0,
        ["data/input.csv"],
    )
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv"]
    assert "memory_summary" in report
    assert report["memory_summary"] == "memory/memory_summary.md"


def test_build_report_zero_rows():
    report = build_report([], [], 0, [])
    assert report["processed_count"] == 0
    assert report["rejected_count"] == 0
    assert report["retry_count"] == 0
    assert report["source_files"] == []


def test_write_report_creates_file():
    out = REPO / "tmp" / "test_report_out.json"
    report = build_report([{"id": "a"}], [], 0, ["f.csv"])
    write_report(report, str(out))
    assert out.exists()
    with open(out) as f:
        loaded = json.load(f)
    assert loaded["processed_count"] == 1


def test_validate_report_valid():
    report = {
        "processed_count": 4,
        "rejected_count": 2,
        "retry_count": 0,
        "source_files": ["a.csv"],
    }
    assert validate_report(report) == []


def test_validate_report_missing_field():
    assert len(validate_report({"processed_count": 1})) > 0


def test_validate_report_wrong_type():
    report = {
        "processed_count": "not_an_int",
        "rejected_count": 0,
        "retry_count": 0,
        "source_files": ["a.csv"],
    }
    errs = validate_report(report)
    assert any("processed_count" in e for e in errs)


def test_validate_report_bad_source_files():
    report = {
        "processed_count": 1,
        "rejected_count": 0,
        "retry_count": 0,
        "source_files": [123],
    }
    errs = validate_report(report)
    assert any("source_files" in e for e in errs)
