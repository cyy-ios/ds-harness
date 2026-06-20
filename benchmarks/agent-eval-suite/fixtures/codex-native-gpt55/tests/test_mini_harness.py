import json
import os
import subprocess
import sys

from mini_harness.config import load_config
from mini_harness.report import build_report
from mini_harness.runner import (
    HarnessError,
    _run_stage,
    clean_records,
    repo_root,
    run_dag,
)


def _last_json_object(text):
    decoder = json.JSONDecoder()
    last = None
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            last = value
    if last is None:
        raise AssertionError(f"no JSON object found in output: {text!r}")
    return last


def test_run_dag_handles_csv_jsonl_and_reports_counts():
    root = repo_root()

    result = run_dag(["data/input.csv", "data/events.jsonl"], root=root)

    assert result.report == {
        "processed_count": 4,
        "rejected_count": 2,
        "retry_count": 0,
        "source_files": ["data/input.csv", "data/events.jsonl"],
    }
    assert [entry["stage"] for entry in result.logs] == ["extract", "clean", "report"]
    assert all({"attempt", "stage", "status"} <= entry.keys() for entry in result.logs)


def test_report_module_builds_required_summary_fields():
    report = build_report(
        records=[{"id": "1"}, {"id": "2"}],
        rejects=[{"reason": "missing_id"}],
        retry_count=1,
        source_files=["data/input.csv"],
    )

    assert report == {
        "processed_count": 2,
        "rejected_count": 1,
        "retry_count": 1,
        "source_files": ["data/input.csv"],
    }


def test_clean_records_normalizes_fields_and_rejects_missing_id():
    records, rejects = clean_records(
        [
            {"ID": "1", "User Name": "Ada", "eventType": "view"},
            {"ID": "", "User Name": "Missing"},
            {"ID": "   ", "User Name": "Blank"},
            {"ID": "", "User Name": ""},
        ]
    )

    assert records == [{"id": "1", "user_name": "Ada", "event_type": "view"}]
    assert [reject["reason"] for reject in rejects] == ["missing_id", "missing_id"]


def test_clean_records_drops_empty_jsonl_objects_with_source_metadata():
    records, rejects = clean_records([{"_source_file": "data/events.jsonl"}])

    assert records == []
    assert rejects == []


def test_stage_retry_limit_is_capped_at_two_and_logged():
    logs = []
    attempts = {"count": 0}

    def fail_three_times():
        attempts["count"] += 1
        if attempts["count"] < 4:
            raise ValueError("temporary")
        return "ok"

    try:
        _run_stage("extract", fail_three_times, logs, max_retries=5)
    except HarnessError:
        pass
    else:
        raise AssertionError("stage should fail after the capped retry limit")

    assert attempts["count"] == 3
    assert [entry["attempt"] for entry in logs] == [1, 2, 3]
    assert [entry["status"] for entry in logs] == ["retrying", "retrying", "failed"]


def test_cli_run_writes_report_rejects_and_logs():
    root = repo_root()
    report_path = root / "evidence" / "test_report.json"
    rejects_path = root / "evidence" / "test_rejects.jsonl"
    log_path = root / "logs" / "test_mini_harness.jsonl"
    for path in (report_path, rejects_path, log_path):
        path.unlink(missing_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "mini_harness",
                "run",
                "--input",
                "data/m4_noise_test.csv",
                "--output",
                "evidence/test_report.json",
                "--rejects-output",
                "evidence/test_rejects.jsonl",
                "--log-output",
                "logs/test_mini_harness.jsonl",
            ],
            cwd=root / "subdir" / "workbench",
            text=True,
            capture_output=True,
            check=True,
            env=env,
        )

        assert _last_json_object(completed.stdout)["processed_count"] == 2
        assert json.loads(report_path.read_text(encoding="utf-8")) == {
            "processed_count": 2,
            "rejected_count": 1,
            "retry_count": 0,
            "source_files": ["data/m4_noise_test.csv"],
        }
        assert len(rejects_path.read_text(encoding="utf-8").splitlines()) == 1
        assert len(log_path.read_text(encoding="utf-8").splitlines()) == 3
    finally:
        for path in (report_path, rejects_path, log_path):
            path.unlink(missing_ok=True)


def test_cli_stdout_report_survives_debug_noise():
    noisy_stdout = "\n".join(
        [
            "debug: extract read 3000 records",
            '{"stage":"extract","status":"ok"}',
            "debug: clean wrote verbose diagnostics",
            '{"processed_count":2,"rejected_count":1,"retry_count":0}',
            "",
        ]
    )

    assert _last_json_object(noisy_stdout) == {
        "processed_count": 2,
        "rejected_count": 1,
        "retry_count": 0,
    }


def test_explicit_json_config_drives_cli_run():
    root = repo_root()
    config_path = root / "evidence" / "test_harness_config.json"
    report_path = root / "evidence" / "config_report.json"
    rejects_path = root / "evidence" / "config_rejects.jsonl"
    log_path = root / "logs" / "config_mini_harness.jsonl"
    for path in (config_path, report_path, rejects_path, log_path):
        path.unlink(missing_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    config_path.write_text(
        json.dumps(
            {
                "inputs": ["data/events.jsonl"],
                "output": "evidence/config_report.json",
                "rejects_output": "evidence/config_rejects.jsonl",
                "log_output": "logs/config_mini_harness.jsonl",
                "max_retries": 2,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        subprocess.run(
            [sys.executable, "-m", "mini_harness", "run", "--config", str(config_path)],
            cwd=root / "subdir" / "workbench",
            text=True,
            capture_output=True,
            check=True,
            env=env,
        )

        assert json.loads(report_path.read_text(encoding="utf-8")) == {
            "processed_count": 2,
            "rejected_count": 1,
            "retry_count": 0,
            "source_files": ["data/events.jsonl"],
        }
    finally:
        for path in (config_path, report_path, rejects_path, log_path):
            path.unlink(missing_ok=True)


def test_yaml_config_and_missing_default_config():
    root = repo_root()
    config_path = root / "evidence" / "test_harness_config.yaml"
    config_path.unlink(missing_ok=True)
    config_path.write_text(
        "\n".join(
            [
                "inputs:",
                "  - data/m4_noise_test.csv",
                "output: evidence/from_yaml.json",
                "rejects_output: evidence/from_yaml_rejects.jsonl",
                "log_output: logs/from_yaml.jsonl",
                "max_retries: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        config = load_config(config_path, root)
        defaults = load_config(root=root)

        assert config.inputs == ["data/m4_noise_test.csv"]
        assert config.max_retries == 1
        assert defaults.inputs == ["data/input.csv", "data/events.jsonl"]
    finally:
        config_path.unlink(missing_ok=True)
