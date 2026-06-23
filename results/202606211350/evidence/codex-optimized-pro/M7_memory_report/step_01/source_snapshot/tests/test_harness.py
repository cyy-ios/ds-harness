"""Test suite for mini_harness per M1-M6 scenarios from memory_summary.md."""

import json
import sys
from pathlib import Path

import pytest

# Ensure src is on path for direct test runs
_repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo / "src"))

from mini_harness.runner import HarnessError, run_dag, _to_snake_case, _extract, _clean
from mini_harness.config import load_config


# ---------------------------------------------------------------------------
# M1: Basic CSV + JSONL processing
# ---------------------------------------------------------------------------

def test_to_snake_case():
    assert _to_snake_case("User Name") == "user_name"
    assert _to_snake_case("eventType") == "event_type"
    assert _to_snake_case("ID") == "id"
    assert _to_snake_case("MyURLParser") == "my_url_parser"


def test_clean_rejects_missing_id():
    records = [
        {"id": "1", "name": "Alice"},
        {"name": "No ID"},
        {"id": "", "name": "Empty ID"},
        {"id": "3", "score": "10"},
    ]
    clean_rows, rejects = _clean(records)
    assert len(clean_rows) == 2
    assert len(rejects) == 2
    assert rejects[0]["name"] == "No ID"
    assert rejects[1]["name"] == "Empty ID"


# ---------------------------------------------------------------------------
# M2: Retry mechanism
# ---------------------------------------------------------------------------

_call_count = 0


def _fail_then_pass():
    global _call_count
    _call_count += 1
    if _call_count < 2:
        raise RuntimeError("transient")
    return "ok"


def test_retry_runner_eventually_succeeds():
    global _call_count
    _call_count = 0
    from mini_harness.runner import _run_stage_with_retry, _write_log
    p = Path("tmp")
    p.mkdir(exist_ok=True)
    log_dir = p
    try:
        result = _run_stage_with_retry("test", _fail_then_pass, 2, log_dir)
        assert result == "ok"
        assert _call_count == 2
    finally:
        pass


def test_retry_exhausted_raises_harness_error():
    def always_fail():
        raise ValueError("boom")

    from mini_harness.runner import _run_stage_with_retry
    log_dir = Path("tmp")
    log_dir.mkdir(exist_ok=True)
    with pytest.raises(HarnessError, match="boom"):
        _run_stage_with_retry("test", always_fail, 1, log_dir)


# ---------------------------------------------------------------------------
# M3: Rejects coverage
# ---------------------------------------------------------------------------

def test_rejects_from_extract_and_clean():
    rows = [
        {"id": "1", "user name": "Alice", "Score": "10"},
        {"id": None, "user name": "Bob"},
        {"id": "2", "user name": "Charlie", "Score": "20"},
        {"user name": "Dan"},
    ]
    clean_rows, rejects = _clean(rows)
    assert len(clean_rows) == 2
    assert len(rejects) == 2
    # snake_case keys in clean
    assert "user_name" in clean_rows[0]
    assert "score" in clean_rows[0]
    # snake_case keys in rejects too
    assert rejects[0]["user_name"] == "Bob"


# ---------------------------------------------------------------------------
# M4: Report fields
# ---------------------------------------------------------------------------

def test_report_dict_fields():
    """Verify report produced by run_dag has the required fields."""
    result = run_dag(
        source_files=["data/input.csv", "data/events.jsonl"],
        output="tmp/test_report_m4.json",
    )
    for key in ("processed_count", "rejected_count", "retry_count", "source_files"):
        assert key in result, f"missing key: {key}"
    assert result["processed_count"] == 4
    assert result["rejected_count"] == 2
    assert isinstance(result["source_files"], list)


# ---------------------------------------------------------------------------
# M5: Config loading (defaults, YAML, JSON)
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = load_config(None)
    assert cfg["retry_max"] == 2
    assert cfg["log_dir"] == "logs"


def test_config_yaml(tmp_path):
    yml = tmp_path / "cfg.yaml"
    yml.write_text("retry_max: 3\n", encoding="ascii")
    cfg = load_config(str(yml))
    assert cfg["retry_max"] == 3


def test_config_json(tmp_path):
    js = tmp_path / "cfg.json"
    js.write_text('{"retry_max": 1}', encoding="ascii")
    cfg = load_config(str(js))
    assert cfg["retry_max"] == 1


# ---------------------------------------------------------------------------
# M6: CLI integration
# ---------------------------------------------------------------------------

def test_cli_run_subcommand(capsys):
    from mini_harness.cli import main
    main([
        "run",
        "data/input.csv",
        "data/events.jsonl",
        "--output", "tmp/test_cli_m6.json",
    ])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2


def test_harness_error_export():
    """M6: run_dag and HarnessError must be importable from mini_harness."""
    from mini_harness import run_dag, HarnessError
    assert run_dag is not None
    assert HarnessError is not None
