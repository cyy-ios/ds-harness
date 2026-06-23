from mini_harness.report import build_report


def test_build_report_contains_stable_contract_fields():
    report = build_report(
        [{"id": "1"}],
        [{"id": ""}],
        0,
        ["data/input.csv"],
        [{"attempt": 1, "stage": "report", "status": "ok"}],
    )

    assert report["processed_count"] == 1
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv"]
    assert report["memory_reference"] == "memory/memory_summary.md"
