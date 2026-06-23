import json

from mini_harness.runner import REPO_ROOT, run_dag


def test_noisy_csv_comments_are_ignored_and_logged():
    output = "tmp/m4-noise-report.json"
    output_path = REPO_ROOT / output
    try:
        report = run_dag(["data/m4_noise_test.csv"], output)

        assert report["processed_count"] == 2
        assert report["rejected_count"] == 1
        assert report["retry_count"] == 0
        assert report["source_files"] == ["data/m4_noise_test.csv"]
        assert [entry["stage"] for entry in report["logs"]] == [
            "extract",
            "clean",
            "report",
        ]
        assert all(
            {"attempt", "stage", "status"}.issubset(entry) for entry in report["logs"]
        )
        assert json.loads(output_path.read_text(encoding="utf-8"))["processed_count"] == 2
    finally:
        output_path.unlink(missing_ok=True)
