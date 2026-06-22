"""M4: Verify long logs and noisy CSV processing.

The test ensures that comment lines in CSV are skipped,
noisy logs are produced, and data/m4_noise_test.csv is processed correctly.
"""
import json
import sys
from pathlib import Path

REPO = Path(r"C:\项目\ds-harness\tmp\agent-eval-fixture-20260621230522")
sys.path.insert(0, str(REPO))

from mini_harness.runner import run_dag


def test_m4_noise_csv_with_comments():
    """data/m4_noise_test.csv has # comment lines that must be skipped."""
    out = REPO / "tmp" / "acceptance-m4-noise-report.json"
    result = run_dag(
        [str(REPO / "data" / "m4_noise_test.csv")],
        str(out),
        repo_root=str(REPO),
        log_dir=str(REPO / "logs"),
    )
    with open(result) as f:
        report = json.load(f)
    # c1,Charlie,30 -> processed
    # ,BadRow,0 -> rejected (no id)
    # c2,Diana,40 -> processed
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0


def test_m4_noise_logs_produced():
    """The log file must contain log entries from the run."""
    log_path = REPO / "logs" / "dag.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    # Must contain stage entries
    assert "stage=extract" in content
    assert "stage=clean" in content
    assert "stage=report" in content
    # Must contain status markers
    assert "status=ok" in content


def test_m4_noise_csv_exists():
    """Sanity: the noise CSV fixture must exist."""
    p = REPO / "data" / "m4_noise_test.csv"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "c1" in content
    assert "c2" in content
    assert "# comment" in content.lower()
