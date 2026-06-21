import json
import subprocess
import sys

from mini_harness.runner import HarnessError, run_dag


def test_run_dag_writes_report(tmp_path):
    output = "tmp/test-report.json"

    report = run_dag(["data/input.csv", "data/events.jsonl"], output)

    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv", "data/events.jsonl"]
    assert [entry["stage"] for entry in report["logs"]] == ["extract", "clean", "report"]

    with open(output, encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved == report


def test_module_cli_run():
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "mini_harness",
            "run",
            "data/input.csv",
            "data/events.jsonl",
            "--output",
            "tmp/cli-report.json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2


def test_rejects_paths_outside_repo():
    try:
        run_dag(["../outside.csv"], "tmp/out.json")
    except HarnessError as exc:
        assert "escapes repo root" in str(exc)
    else:
        raise AssertionError("expected HarnessError")
