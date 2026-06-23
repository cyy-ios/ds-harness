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

    def test_retry_increases_retry_count(self, data_dir, tmp_out, monkeypatch):
        """A transient failure in _extract causes retry and increments retry_count."""
        import mini_harness.runner as runner
        from unittest.mock import MagicMock

        call_count = [0]
        orig_extract = runner._extract

        def flaky_extract(sources):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("transient error")
            return orig_extract(sources)

        monkeypatch.setattr(runner, "_extract", flaky_extract)
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        assert report["retry_count"] == 1, f"expected 1 retry, got {report['retry_count']}"
        failed_entries = [
            e for e in report["logs"]
            if e["status"] == "failed"
        ]
        assert len(failed_entries) == 1, f"expected 1 failed, got {len(failed_entries)}"
        assert failed_entries[0]["attempt"] == 1
        assert "transient error" in failed_entries[0].get("detail", "")

    def test_retry_exhaustion_raises(self, data_dir, tmp_out, monkeypatch):
        """A stage that fails 3 times (attempt 1 + 2 retries) raises HarnessError."""
        import mini_harness.runner as runner

        call_count = [0]

        def always_fail_extract(sources):
            call_count[0] += 1
            raise OSError("persistent failure")

        monkeypatch.setattr(runner, "_extract", always_fail_extract)
        path = os.path.join(data_dir, "input.csv")

        with pytest.raises(HarnessError, match="DAG failed after 3 attempts"):
            run_dag([path], tmp_out)

        # Should have been called 3 times (initial + 2 retries)
        assert call_count[0] == 3

    def test_retry_logs_structure(self, data_dir, tmp_out, monkeypatch):
        """Retry logs contain attempt numbers, stage, status, and detail."""
        import mini_harness.runner as runner

        call_count = [0]
        orig_extract = runner._extract

        def flaky_extract(sources):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("transient on attempt 1")
            return orig_extract(sources)

        monkeypatch.setattr(runner, "_extract", flaky_extract)
        path = os.path.join(data_dir, "input.csv")
        report = run_dag([path], tmp_out)

        # Log should have entries for both attempts
        attempts = set(e["attempt"] for e in report["logs"])
        assert 1 in attempts
        assert 2 in attempts

        # Check failed entry
        failed = [e for e in report["logs"] if e["status"] == "failed"]
        assert len(failed) == 1
        assert failed[0]["attempt"] == 1
        assert failed[0]["stage"] == "error"
        assert "transient" in failed[0]["detail"]

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
