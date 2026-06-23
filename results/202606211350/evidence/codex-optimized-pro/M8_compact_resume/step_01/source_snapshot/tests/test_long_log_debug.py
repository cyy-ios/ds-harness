"""M4: Verify long log output and noisy CSV processing.

Ensures logs/ directory contains valid JSONL entries and that
data/m4_noise_test.csv is processed correctly despite comment lines.
"""

import json
from pathlib import Path

import sys
_repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo / "src"))

from mini_harness.runner import _extract, _clean


def test_noisy_csv_processing():
    """m4_noise_test.csv has comment lines and a row with missing ID."""
    repo = Path(__file__).resolve().parent.parent
    csv_path = str(repo / "data" / "m4_noise_test.csv")
    records = _extract([csv_path])
    assert len(records) >= 2, f"expected at least 2 data rows, got {len(records)}"
    clean_rows, rejects = _clean(records)
    # c1 (id=c1) and c2 (id=c2) should pass; row with empty id rejected
    assert len(clean_rows) >= 2, f"expected >=2 clean, got {len(clean_rows)}"
    assert len(rejects) >= 1, f"expected >=1 reject, got {len(rejects)}"


def test_log_output_present():
    """Verify log files exist under logs/ and contain valid JSONL entries."""
    repo = Path(__file__).resolve().parent.parent
    log_dir = repo / "logs"
    assert log_dir.is_dir(), f"logs directory not found: {log_dir}"
    log_files = sorted(log_dir.glob("harness_*.jsonl"))
    assert len(log_files) > 0, "no harness log files found"
    for lf in log_files:
        text = lf.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            assert "attempt" in entry, f"missing attempt in {lf.name}"
            assert "stage" in entry, f"missing stage in {lf.name}"
            assert "status" in entry, f"missing status in {lf.name}"
            assert entry["status"] in ("started", "ok", "failed"), \
                f"unexpected status {entry['status']} in {lf.name}"
