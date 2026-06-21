import json
import subprocess
import sys
from pathlib import Path

from mini_harness.runner import HarnessError, run_dag


def test_run_dag_writes_report(tmp_path):
    output = "tmp/test-report.json"

    report = run_dag(["data/input.csv", "data/events.jsonl"], output)

    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2
    assert report["retry_count"] == 0
    assert report["source_files"] == ["data/input.csv", "data/events.jsonl"]
    assert [entry["stage"] for entry in report["logs"]] == ["extract", "clean", "report"]
    assert report["records"][0] == {"id": "1", "user_name": "Alice", "score": "10"}
    assert report["records"][2] == {"id": "e1", "event_type": "click"}
    assert len(report["rejects"]) == 2

    with open(output, encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved == report


def test_extract_retries_once_and_reports_real_counts(monkeypatch):
    from mini_harness import runner

    calls = {"count": 0}
    original = runner._read_csv

    def flaky_read_csv(path):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("temporary read failure")
        return original(path)

    monkeypatch.setattr(runner, "_read_csv", flaky_read_csv)

    report = run_dag(["data/input.csv"], "tmp/retry-report.json")

    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 1
    assert report["logs"][0]["status"] == "failed"
    assert report["logs"][1]["attempt"] == 2


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


def test_cli_run_with_json_config():
    Path("tmp/json-config.json").parent.mkdir(parents=True, exist_ok=True)
    Path("tmp/json-config.json").write_text(
        json.dumps({"sources": ["data/input.csv", "data/events.jsonl"], "output": "tmp/json-report.json"}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-B", "-m", "mini_harness", "run", "--config", "tmp/json-config.json"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["processed_count"] == 4
    assert Path("tmp/json-report.json").exists()


def test_cli_run_with_yaml_config_and_cli_output_override():
    Path("tmp/yaml-config.yaml").parent.mkdir(parents=True, exist_ok=True)
    Path("tmp/yaml-config.yaml").write_text(
        "sources:\n  - data/input.csv\n  - data/events.jsonl\noutput: tmp/ignored-report.json\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "mini_harness",
            "run",
            "--config",
            "tmp/yaml-config.yaml",
            "--output",
            "tmp/yaml-report.json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["rejected_count"] == 2
    assert Path("tmp/yaml-report.json").exists()


def test_rejects_paths_outside_repo():
    try:
        run_dag(["../outside.csv"], "tmp/out.json")
    except HarnessError as exc:
        assert "escapes repo root" in str(exc)
    else:
        raise AssertionError("expected HarnessError")
