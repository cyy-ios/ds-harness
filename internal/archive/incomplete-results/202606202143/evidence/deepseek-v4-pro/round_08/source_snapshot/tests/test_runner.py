import json
import pytest
from pathlib import Path
from mini_harness.runner import Runner, MAX_RETRIES


def test_runner_happy_path(tmp_path):
    # Create input files
    csv_file = tmp_path / "input.csv"
    csv_file.write_text("ID,Name\n1,Alice\n2,Bob")
    input_files = [str(csv_file)]
    runner = Runner(input_files)
    report = runner.run()
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 0
    assert report["retry_count"] == 0
    assert report["source_files"] == input_files


def test_runner_with_rejects(tmp_path):
    csv_file = tmp_path / "input.csv"
    csv_file.write_text("ID,Name\n1,Alice\n,Bad\n2,Bob")
    runner = Runner([str(csv_file)])
    report = runner.run()
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1


def test_runner_jsonl(tmp_path):
    jsonl_file = tmp_path / "data.jsonl"
    jsonl_file.write_text('{"id":"e1","eventType":"click"}\n{"eventType":"missing"}\n{"id":"e2","eventType":"view"}')
    runner = Runner([str(jsonl_file)])
    report = runner.run()
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1


def test_runner_logs_on_success(tmp_path):
    csv_file = tmp_path / "input.csv"
    csv_file.write_text("ID,Name\n1,Alice")
    runner = Runner([str(csv_file)])
    runner.run()
    assert len(runner.logs) == 3  # extract, clean, report success
    for log_entry in runner.logs:
        assert log_entry["status"] == "success"
    stages = [log["stage"] for log in runner.logs]
    assert stages == ["extract", "clean", "report"]


def test_runner_retry_on_extract_failure(tmp_path, monkeypatch):
    # Simulate failure on first extract attempt
    original_extract = Runner.extract
    call_count = 0

    def failing_extract(self):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            raise ValueError("simulated extract failure")
        return original_extract(self)

    monkeypatch.setattr(Runner, "extract", failing_extract)

    csv_file = tmp_path / "input.csv"
    csv_file.write_text("ID,Name\n1,Alice")
    runner = Runner([str(csv_file)])
    report = runner.run()
    assert report["retry_count"] == 1
    # Check logs: extract had one failure then success, clean and report success
    extract_logs = [log for log in runner.logs if log["stage"] == "extract"]
    assert len(extract_logs) == 2
    assert extract_logs[0]["status"] == "failure"
    assert extract_logs[1]["status"] == "success"


def test_runner_retry_exhaustion(tmp_path, monkeypatch):
    # Always fail extract
    def always_fail(self):
        raise ValueError("permanent failure")

    monkeypatch.setattr(Runner, "extract", always_fail)

    csv_file = tmp_path / "input.csv"
    csv_file.write_text("ID,Name\n1,Alice")
    runner = Runner([str(csv_file)])
    with pytest.raises(ValueError):
        runner.run()
    # Should have 3 attempts (1 initial + 2 retries)
    assert runner.extract_stage.attempt == MAX_RETRIES + 1
    assert runner.retry_count == MAX_RETRIES
    extract_logs = [log for log in runner.logs if log["stage"] == "extract"]
    assert all(log["status"] == "failure" for log in extract_logs)
    assert len(extract_logs) == MAX_RETRIES + 1
