from mini_harness.report import build_report


def test_build_report_counts_current_records_and_cites_memory_summary():
    report = build_report(
        processed_records=[{"id": "1"}, {"id": "2"}],
        rejects=[{"reason": "missing_id"}],
        retry_count=0,
        source_files=["data/input.csv"],
        logs=[{"attempt": 1, "stage": "report", "status": "succeeded"}],
    )

    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv"]
    assert report["memory_summary"] == "memory/memory_summary.md"

