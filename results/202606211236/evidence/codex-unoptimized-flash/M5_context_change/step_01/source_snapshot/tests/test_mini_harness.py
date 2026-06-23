import json

from mini_harness.cli import main
from mini_harness.runner import HarnessError, run_dag

REPO_ROOT = run_dag.__globals__["REPO_ROOT"]


def test_run_dag_writes_report():
    output = "tmp/test-report.json"

    output_path = REPO_ROOT / output
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


def test_run_dag_retries_failed_stage(monkeypatch):
    output = "tmp/retry-report.json"
    output_path = REPO_ROOT / output
    import mini_harness.runner as runner

    original_read_csv = runner._read_csv
    calls = {"count": 0}

    def flaky_read_csv(path):
        calls["count"] += 1
        if calls["count"] == 1:
            raise HarnessError("temporary extract failure")
        return original_read_csv(path)

    monkeypatch.setattr(runner, "_read_csv", flaky_read_csv)
    try:
        report = run_dag(["data/input.csv", "data/events.jsonl"], output)
        assert report["retry_count"] == 1
        assert report["processed_count"] == 4
        assert report["rejected_count"] == 2
        assert report["logs"][0]["status"] == "failed"
        assert report["logs"][1]["attempt"] == 2
        assert json.loads(output_path.read_text(encoding="utf-8"))["retry_count"] == 1
    finally:
        output_path.unlink(missing_ok=True)


def test_run_cli_uses_explicit_json_config(capsys):
    config_path = REPO_ROOT / "tmp/test-harness.json"
    output_path = REPO_ROOT / "tmp/json-config-report.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "sources": ["data/input.csv", "data/events.jsonl"],
                "output": "tmp/json-config-report.json",
            }
        ),
        encoding="utf-8",
    )
    try:
        assert main(["run", "--config", "tmp/test-harness.json"]) == 0
        stdout = capsys.readouterr().out
        summary = json.loads(stdout)
        assert summary == {
            "output": "tmp/json-config-report.json",
            "processed_count": 4,
            "rejected_count": 2,
            "retry_count": 0,
        }
        assert "records" not in summary
        assert len(stdout) < 200
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["processed_count"] == 4
        assert report["rejected_count"] == 2
    finally:
        config_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def test_run_cli_uses_explicit_yaml_config_with_cli_override():
    config_path = REPO_ROOT / "tmp/test-harness.yaml"
    output_path = REPO_ROOT / "tmp/yaml-config-report.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "\n".join(
            [
                "sources:",
                "  - data/input.csv",
                "  - data/events.jsonl",
                "output: tmp/unused-report.json",
            ]
        ),
        encoding="utf-8",
    )
    try:
        assert (
            main(
                [
                    "run",
                    "--config",
                    "tmp/test-harness.yaml",
                    "--output",
                    "tmp/yaml-config-report.json",
                ]
            )
            == 0
        )
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["source_files"] == ["data/input.csv", "data/events.jsonl"]
    finally:
        config_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        (REPO_ROOT / "tmp/unused-report.json").unlink(missing_ok=True)


def test_run_cli_uses_default_repo_config():
    config_path = REPO_ROOT / "harness.json"
    output_path = REPO_ROOT / "tmp/default-config-report.json"
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    config_path.write_text(
        json.dumps(
            {
                "sources": ["data/input.csv", "data/events.jsonl"],
                "output": "tmp/default-config-report.json",
            }
        ),
        encoding="utf-8",
    )
    try:
        assert main(["run"]) == 0
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["processed_count"] == 4
    finally:
        if original is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(original, encoding="utf-8")
        output_path.unlink(missing_ok=True)
