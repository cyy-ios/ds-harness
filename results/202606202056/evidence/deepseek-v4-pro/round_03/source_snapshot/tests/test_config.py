"""Tests for config loading."""
import json
import os
import tempfile
import pytest

from mini_harness.config import load_config


def test_load_defaults_no_path():
    cfg = load_config()
    assert cfg == {
        "input_files": [],
        "max_retries": 2,
        "log_level": "INFO"
    }


def test_load_json_config():
    data = {"input_files": ["a.csv"], "max_retries": 1}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        tmp_path = f.name
    try:
        cfg = load_config(tmp_path)
        assert cfg["input_files"] == ["a.csv"]
        assert cfg["max_retries"] == 1
        assert cfg["log_level"] == "INFO"  # default value persists
    finally:
        os.unlink(tmp_path)


def test_load_yaml_config():
    yaml_content = "input_files: b.csv\nmax_retries: 3\nlog_level: DEBUG"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name
    try:
        cfg = load_config(tmp_path)
        assert cfg["input_files"] == "b.csv"  # YAML parser returns a scalar, not list
        assert cfg["max_retries"] == 3
        assert cfg["log_level"] == "DEBUG"
    finally:
        os.unlink(tmp_path)
