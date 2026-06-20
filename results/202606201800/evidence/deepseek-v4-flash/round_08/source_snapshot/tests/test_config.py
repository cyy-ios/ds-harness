import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import json
import tempfile

from pathlib import Path
from mini_harness.config import load_config

def test_load_empty_config():
    result = load_config(Path("nonexistent.json"))
    assert result == {}

def test_load_json_config():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"key": "value"}, f)
        temp_path = f.name
    result = load_config(Path(temp_path))
    assert result == {"key": "value"}
    os.unlink(temp_path)
