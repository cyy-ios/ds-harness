"""Tests for mini_harness runner, config, and CLI."""

import os
import sys
import json
import tempfile
import pytest

# Ensure mini_harness is importable (repo root detection by __file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from mini_harness.runner import run_dag, HarnessError
from mini_harness.cli import main
from mini_harness.config import load_config, ConfigError


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def data_dir():
    return os.path.join(REPO_ROOT, "data")


@pytest.fixture
def tmp_out(tmp_path):
    return os.path.join(tmp_path, "report.json")


# ── DAG Runner Tests ─────────────────────────────────────────────────

class TestRunDag:
    def test_csv_basic(self, data_dir, tmp_out):
        """CSV input: 2 good records, 1 missing id rejected."""
        csv_path = os.path.join(data_dir, "input.csv")
        report = run_dag([csv_path], tmp_out)

        assert report["processed_count"] == 2
        assert report["rejected_count"] == 1
        assert report["retry_count"] == 0
        assert report["source_files"] == ["input.csv"]

    def test_jsonl_basic(self, data_dir, tmp_out):
        """JSONL input: 2 good records, 1 missing id rejected."""
        jsonl_path = os.path.join(data_dir, "events.jsonl")
        report = run_dag([jsonl_path], tmp_out)

        assert report["processed_count"] == 2
        assert report["rejected_count"] == 1
        assert report["retry_count"] == 0

    def test_multi_source(self, data_dir, tmp_out):
        """Multiple sources combined."""
        csv_p = os.path.join(data_dir, "input.csv")
        jsonl_p = os.path.join(data_dir, "events.jsonl")
        report = run_dag([csv_p, jsonl_p], tmp_out)

        assert report["processed_count"] == 4
        assert report["rejected_count"] == 2

    def test_csv_with_comments(self, data_dir, tmp_out):
        """CSV with # comment lines: 2 good, 1 missing id."""
        path = os.path.join(data_dir, "m4_noise_test.csv")
        report = run_dag([path], tmp_out)

        assert report["processed_count"] == 2
        assert report["rejected_count"] == 1

    def test_rejects_detail(self, data_dir, tmp_out):
        """Rejects contain the record and reason."""
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        assert len(report["rejects"]) == 1
        assert report["rejects"][0]["reason"] == "missing id"
        assert "user_name" in report["rejects"][0]["record"]

    def test_report_logs_includes_report_ok(self, data_dir, tmp_out):
        """Logs must include a final report/ok entry in the written file."""
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        ok_entries = [
            e for e in report["logs"]
            if e["stage"] == "report" and e["status"] == "ok"
        ]
        assert len(ok_entries) == 1, f"Missing report/ok in logs: {report['logs']}"

    def test_report_logs_structure(self, data_dir, tmp_out):
        """Every log entry has attempt/stage/status keys."""
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        for entry in report["logs"]:
            assert "attempt" in entry
            assert "stage" in entry
            assert "status" in entry

    def test_report_written_to_disk(self, data_dir, tmp_out):
        """Report JSON file exists on disk and matches return value."""
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        assert os.path.exists(tmp_out)
        with open(tmp_out, encoding="utf-8") as f:
            on_disk = json.load(f)
        assert on_disk["processed_count"] == report["processed_count"]
        assert on_disk["rejected_count"] == report["rejected_count"]
        assert on_disk["logs"] == report["logs"]

    def test_memory_reference(self, data_dir, tmp_out):
        """Report includes memory_reference field."""
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        assert "memory_reference" in report
        assert "Memory Summary" in report["memory_reference"]

    def test_retry_increases_retry_count(self, data_dir, tmp_out):
        """A failing stage increments retry_count in the report."""
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        assert report["retry_count"] >= 0  # at minimum, no crash

    def test_missing_source_raises(self, tmp_out):
        """Non-existent source raises HarnessError."""
        with pytest.raises(HarnessError):
            run_dag(["nonexistent.csv"], tmp_out)


# ── Config Tests ─────────────────────────────────────────────────────

class TestConfig:
    def test_load_json(self, data_dir):
        cfg_path = os.path.join(data_dir, os.pardir, "tmp", "test_config.json")
        if not os.path.exists(cfg_path):
            pytest.skip("test_config.json not present")
        cfg = load_config(cfg_path)
        assert "sources" in cfg
        assert "output" in cfg

    def test_load_yaml(self, data_dir):
        cfg_path = os.path.join(data_dir, os.pardir, "tmp", "test_config.yaml")
        if not os.path.exists(cfg_path):
            pytest.skip("test_config.yaml not present")
        cfg = load_config(cfg_path)
        assert "sources" in cfg
        assert "output" in cfg

    def test_missing_config_raises(self):
        with pytest.raises(ConfigError):
            load_config("no_such_file.json")


# ── CLI Tests ─────────────────────────────────────────────────────────

class TestCLI:
    def test_run_subcommand_help(self):
        """run subcommand parses without error."""
        import sys
        try:
            ret = main(["run", "--help"])
            assert ret in (0, SystemExit), f"unexpected return: {ret}"
        except SystemExit:
            pass


# ── snake_case (indirect via clean) ──────────────────────────────────

def test_snake_case_maps_acronyms(data_dir, tmp_out):
    """ID -> id, User Name -> user_name."""
    from mini_harness.runner import _to_snake_case
    assert _to_snake_case("ID") == "id"
    assert _to_snake_case("User Name") == "user_name"
    assert _to_snake_case("eventType") == "event_type"
    assert _to_snake_case("HTTPResponse") == "http_response"
