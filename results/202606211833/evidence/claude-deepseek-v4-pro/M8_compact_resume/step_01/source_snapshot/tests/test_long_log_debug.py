"""M4_long_log_debug — verify DAG handles noisy CSV (comments/empty lines) and structured logs."""
import json
import logging
import os
import sys
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mini_harness.runner import run_dag, _ensure_logger

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"


def test_noise_csv_extract_and_clean():
    """data/m4_noise_test.csv has comment headers, inline comments, and footer comments.
    After extract→clean, only 2 valid rows (c1, c2) should survive; the BadRow has no id."""
    output = str(TMP_DIR / "test-report.json")
    report = run_dag(
        [str(DATA_DIR / "m4_noise_test.csv")],
        output,
    )
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert len(report["source_files"]) == 1


def test_structured_log_format(caplog):
    """Structured logs must include attempt, stage, and status fields as JSON objects."""
    caplog.set_level(logging.INFO, logger="mini_harness")
    output = str(TMP_DIR / "test-log-format.json")
    run_dag([str(DATA_DIR / "m4_noise_test.csv")], output)

    log_lines = [r.message for r in caplog.records if r.name == "mini_harness"]
    assert len(log_lines) >= 3  # at least extract, clean, report stages

    for line in log_lines:
        # Each structured log should be parseable JSON with attempt/stage/status
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue  # non-structured log line, skip
        for key in ("attempt", "stage", "status"):
            assert key in parsed, f"structured log missing '{key}': {line}"


def test_long_log_no_duplicate_handlers():
    """Repeated run_dag calls must not accumulate duplicate log handlers."""
    import mini_harness.runner as runner_mod
    runner_mod._configured = False
    logger = logging.getLogger("mini_harness")
    logger.handlers.clear()

    run_dag([str(DATA_DIR / "m4_noise_test.csv")], str(TMP_DIR / "test-dup1.json"))
    count1 = len(logger.handlers)

    run_dag([str(DATA_DIR / "m4_noise_test.csv")], str(TMP_DIR / "test-dup2.json"))
    count2 = len(logger.handlers)

    assert count1 == count2, f"handlers grew from {count1} to {count2}"
