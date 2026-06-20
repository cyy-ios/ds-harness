import json
import pytest
import yaml
from pathlib import Path
from mini_harness.config import load_config


def test_load_config_json(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"input_files": ["in.csv"], "output": "out.json"}))
    result = load_config(config_file)
    assert result == {"input_files": ["in.csv"], "output": "out.json"}


def test_load_config_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("input_files:\n- in.csv\noutput: out.json")
    result = load_config(config_file)
    assert result == {"input_files": ["in.csv"], "output": "out.json"}


def test_load_config_yml_extension(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("input_files:\n- in.csv")
    result = load_config(config_file)
    assert result == {"input_files": ["in.csv"]}


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config(Path("nonexistent.json"))


def test_load_config_invalid_json(tmp_path):
    config_file = tmp_path / "bad.json"
    config_file.write_text("not json")
    # It should fallback to YAML, but not valid YAML either -> ValueError
    with pytest.raises(ValueError, match="Failed to parse config as JSON or YAML"):
        load_config(config_file)


def test_load_config_yaml_error(tmp_path):
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("\tbad: indentation")  # tabs are invalid in YAML
    with pytest.raises(ValueError, match="Failed to parse config as JSON or YAML"):
        load_config(config_file)
