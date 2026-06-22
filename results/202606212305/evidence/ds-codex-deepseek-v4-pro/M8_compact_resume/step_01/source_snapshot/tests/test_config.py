"""Tests for config module edge cases not covered in test_harness.py."""
import sys
from pathlib import Path

REPO = Path(r"C:\项目\ds-harness\tmp\agent-eval-fixture-20260621230522")
sys.path.insert(0, str(REPO))

from mini_harness.config import load_config, resolve_path, find_config, ConfigError


def test_resolve_relative_path():
    result = resolve_path(str(REPO), "data/input.csv")
    assert result.endswith("data\\input.csv")


def test_resolve_absolute_path():
    abs_path = str(REPO / "data" / "input.csv")
    assert resolve_path(str(REPO), abs_path) == abs_path


def test_find_config_defaults():
    path = find_config(str(REPO))
    assert path is not None


def test_load_config_invalid_yaml():
    """Invalid YAML produces ConfigError, not a crash."""
    bad = REPO / "tmp" / "bad.yaml"
    bad.write_text(": bad key\n", encoding="utf-8")
    try:
        load_config(str(REPO), str(bad))
        assert False, "Expected ConfigError"
    except ConfigError:
        pass


def test_load_config_empty_json():
    empty = REPO / "tmp" / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    cfg = load_config(str(REPO), str(empty))
    assert cfg["max_retries"] == 2  # default


def test_config_default_keys_present():
    cfg = load_config(str(REPO))
    assert "max_retries" in cfg
    assert "log_dir" in cfg
