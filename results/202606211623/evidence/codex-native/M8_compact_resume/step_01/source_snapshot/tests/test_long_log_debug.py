from pathlib import Path

import mini_harness.runner as runner


def test_noisy_csv_lines_are_ignored_without_retrying():
    output = Path(__file__).resolve().parents[1] / "tmp" / "noisy-debug-report.json"
    try:
        report = runner.run_dag(["data/m4_noise_test.csv"], "tmp/noisy-debug-report.json")
    finally:
        output.unlink(missing_ok=True)

    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert [entry["stage"] for entry in report["logs"]] == ["extract", "clean", "report"]
