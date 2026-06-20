import os
import tempfile
import json
from mini_harness.config import Config

def test_load_json_config():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"input_files": ["a.csv"], "output_dir": "out"}, f)
        path = f.name
    try:
        result = Config.load(path)
        assert result == {"input_files": ["a.csv"], "output_dir": "out"}
    finally:
        os.unlink(path)

def test_load_yaml_config():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("input_files:\n- b.jsonl\noutput_dir: out2\n")
        path = f.name
    try:
        result = Config.load(path)
        assert result == {"input_files": ["b.jsonl"], "output_dir": "out2"}
    finally:
        os.unlink(path)

def test_default_config_not_found():
    # Ensure no default config file
    result = Config.load()
    assert result == {}

def test_config_file_not_found():
    import pytest
    with pytest.raises(FileNotFoundError):
        Config.load("nonexistent.yaml")
