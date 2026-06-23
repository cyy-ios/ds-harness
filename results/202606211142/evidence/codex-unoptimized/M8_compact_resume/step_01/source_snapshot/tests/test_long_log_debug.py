from mini_harness.runner import run_dag


def test_noisy_csv_keeps_structured_logs():
    report = run_dag(["data/m4_noise_test.csv"], "tmp/m4-noise-report.json")

    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/m4_noise_test.csv"]
    assert all({"attempt", "stage", "status"} <= set(entry) for entry in report["logs"])
