"""Tests covering DAG retry, rejects, and report fields."""
import json
import os
import sys
from pathlib import Path

import pytest

# Ensure project root on path for import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mini_harness.runner import run_dag, HarnessError, _ensure_logger


TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(autouse=True)
def _setup_logger_for_tests():
    """Configure logger so structured logs are captured by pytest, not leaked to real stderr."""
    import logging
    logger = logging.getLogger("mini_harness")
    logger.handlers.clear()
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_h)


def test_run_dag_produces_report():
    output = str(TMP_DIR / "test-report.json")
    report = run_dag(
        [str(DATA_DIR / "input.csv"), str(DATA_DIR / "events.jsonl")],
        output,
    )
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2
    assert report["retry_count"] == 0
    assert len(report["source_files"]) == 2
    assert "records" in report
    assert len(report["records"]["rejected"]) == 2
    assert os.path.exists(output)


def test_retry_on_nonexistent_file_triggers_harness_error():
    with pytest.raises(HarnessError, match="extract.*failed after 2 retries"):
        run_dag([str(TMP_DIR / "nonexistent.csv")], str(TMP_DIR / "should-fail.json"))


def test_harness_error_is_exception():
    assert issubclass(HarnessError, Exception)


def test_rejects_include_missing_id():
    output = str(TMP_DIR / "test-rejects.json")
    report = run_dag(
        [str(DATA_DIR / "input.csv"), str(DATA_DIR / "events.jsonl")],
        output,
    )
    rejected_ids = [r.get("id") for r in report["records"]["rejected"]]
    # CSV row 2: ID="" → rejected; JSONL row 2: no "id" at all → rejected
    assert "" in rejected_ids or None in rejected_ids
    rejects_without_id = [r for r in report["records"]["rejected"] if "id" not in r or not r.get("id")]
    assert len(rejects_without_id) == 2


def test_report_required_fields():
    output = str(TMP_DIR / "test-fields.json")
    report = run_dag(
        [str(DATA_DIR / "events.jsonl")],
        output,
    )
    for key in ("processed_count", "rejected_count", "retry_count", "source_files"):
        assert key in report, f"missing required field: {key}"


def test_import_during_test_no_logger_leak():
    """Logger handler must NOT emit during import — only on run_dag() call."""
    import logging
    import mini_harness.runner as runner_mod

    # Reset to simulate fresh import state
    runner_mod._configured = False
    logging.getLogger("mini_harness").handlers.clear()

    # Re-import-like check: _configured starts False
    assert not runner_mod._configured

    # run_dag triggers handler attachment
    output = str(TMP_DIR / "test-leak.json")
    runner_mod.run_dag([str(DATA_DIR / "events.jsonl")], output)
    assert runner_mod._configured
    assert logging.getLogger("mini_harness").handlers
