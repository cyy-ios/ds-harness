import json

from mini_harness.runner import HarnessError, run_dag


def test_run_dag_writes_report():
    output = "tmp/test-report.json"

    output_path = run_dag.__globals__["REPO_ROOT"] / output
    try:
        report = run_dag(["data/input.csv", "data/events.jsonl"], output)

        assert report["processed_count"] == 4
        assert report["rejected_count"] == 2
        assert report["retry_count"] == 0
        assert report["source_files"] == ["data/input.csv", "data/events.jsonl"]
        assert report["records"][0] == {"id": "1", "user_name": "Alice", "score": "10"}
        assert report["memory_reference"] == "memory/memory_summary.md"
        assert {entry["stage"] for entry in report["logs"]} == {
            "extract",
            "clean",
            "report",
        }
        assert all(
            {"attempt", "stage", "status"}.issubset(entry) for entry in report["logs"]
        )

        written = json.loads(output_path.read_text())
        assert written["processed_count"] == 4
    finally:
        output_path.unlink(missing_ok=True)


def test_run_dag_rejects_outside_output_path():
    try:
        run_dag(["data/input.csv"], "../outside.json")
    except HarnessError as exc:
        assert "outside repo root" in str(exc)
    else:
        raise AssertionError("expected HarnessError")
