import json
import sys
from pathlib import Path

REPO = Path(r"C:\项目\ds-harness\tmp\agent-eval-fixture-20260621230522")
sys.path.insert(0, str(REPO))

from mini_harness.runner import run_dag, HarnessError
from mini_harness.config import load_config

def test_run_dag_basic():
    out = REPO / "tmp" / "test_run_dag_basic.json"
    result = run_dag(
        [str(REPO / "data" / "input.csv")],
        str(out),
        repo_root=str(REPO),
        log_dir=str(REPO / "logs"),
    )
    with open(result) as f:
        report = json.load(f)
    assert report["processed_count"] == 2
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0

def test_run_dag_missing_file_retry():
    try:
        run_dag(
            [str(REPO / "data" / "nonexistent.csv")],
            str(REPO / "tmp" / "test_retry_out.json"),
            repo_root=str(REPO),
            max_retries=2,
            log_dir=str(REPO / "logs"),
        )
        assert False, "Expected HarnessError"
    except HarnessError:
        pass

def test_load_json_config():
    cfg = load_config(str(REPO), "config.json")
    assert cfg["max_retries"] == 1
    assert cfg["log_dir"] == "json_logs"
    assert "data/input.csv" in cfg["inputs"]

def test_load_yaml_config():
    cfg = load_config(str(REPO), "config.yaml")
    assert cfg["max_retries"] == 3
    assert cfg["log_dir"] == "custom_logs"
    assert len(cfg["inputs"]) == 2

def test_config_missing_returns_defaults():
    cfg = load_config(str(REPO), "nonexistent.json")
    assert cfg["max_retries"] == 2
    assert cfg["log_dir"] == "logs"
