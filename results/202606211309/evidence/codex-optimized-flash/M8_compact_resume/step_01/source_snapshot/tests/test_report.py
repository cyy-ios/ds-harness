"""Tests for mini_harness/report.py."""

import os
import sys
import json
import tempfile
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from mini_harness.report import build_report, write_report


class TestBuildReport:
    def test_counts_and_source_files(self):
        """Basic report fields match inputs."""
        report = build_report(
            clean_records=[{"id": "1", "name": "a"}, {"id": "2", "name": "b"}],
            rejects=[{"record": {}, "reason": "missing id"}],
            retry_count=0,
            source_files=["input.csv"],
            logs=[{"attempt": 1, "stage": "extract", "status": "ok"}],
        )
        assert report["processed_count"] == 2
        assert report["rejected_count"] == 1
        assert report["retry_count"] == 0
        assert report["source_files"] == ["input.csv"]

    def test_empty_inputs(self):
        """All-zero report for empty inputs."""
        report = build_report([], [], 0, [])
        assert report["processed_count"] == 0
        assert report["rejected_count"] == 0
        assert report["retry_count"] == 0
        assert report["source_files"] == []

    def test_logs_omitted_defaults_to_empty(self):
        """When logs is None, report uses empty list."""
        report = build_report([], [], 0, [])
        assert report["logs"] == []

    def test_logs_preserved(self):
        """Logs passed in are preserved in output."""
        logs = [{"attempt": 1, "stage": "extract", "status": "ok"}]
        report = build_report([], [], 0, [], logs=logs)
        assert report["logs"] == logs

    def test_memory_reference_missing_file(self):
        """Non-existent memory_path yields empty string."""
        report = build_report([], [], 0, [], memory_path="/nonexistent/path.md")
        assert report["memory_reference"] == ""

    def test_memory_reference_exists(self, data_dir):
        """Existing memory_summary.md is read into memory_reference."""
        mem_path = os.path.join(data_dir, os.pardir, "memory", "memory_summary.md")
        report = build_report([], [], 0, [], memory_path=mem_path)
        assert "Memory Summary" in report["memory_reference"]
        assert "早期设计决策" in report["memory_reference"]

    def test_rejects_details(self):
        """Rejects and their reasons are preserved."""
        rejects = [
            {"record": {"name": "bad"}, "reason": "missing id"},
        ]
        report = build_report([], rejects, 0, [])
        assert len(report["rejects"]) == 1
        assert report["rejects"][0]["reason"] == "missing id"


class TestWriteReport:
    def test_writes_json(self, tmp_path):
        """write_report creates a valid JSON file."""
        report = {"processed_count": 1, "rejected_count": 0, "retry_count": 0, "source_files": []}
        out = os.path.join(tmp_path, "report.json")
        write_report(report, out)

        assert os.path.exists(out)
        with open(out, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["processed_count"] == 1

    def test_creates_parent_dir(self, tmp_path):
        """Parent directories are created if missing."""
        report = {"processed_count": 0, "rejected_count": 0, "retry_count": 0, "source_files": []}
        out = os.path.join(tmp_path, "sub", "nested", "report.json")
        write_report(report, out)

        assert os.path.exists(out)

    def test_round_trip_preserves_data(self, tmp_path):
        """JSON round-trip preserves all fields."""
        original = {
            "processed_count": 3,
            "rejected_count": 1,
            "retry_count": 1,
            "source_files": ["a.csv", "b.jsonl"],
            "rejects": [{"record": {"x": "y"}, "reason": "missing id"}],
            "logs": [{"attempt": 1, "stage": "clean", "status": "ok"}],
            "memory_reference": "test",
        }
        out = os.path.join(tmp_path, "roundtrip.json")
        write_report(original, out)

        with open(out, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == original


@pytest.fixture
def data_dir():
    return os.path.join(REPO_ROOT, "data")
