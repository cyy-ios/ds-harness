import os
import json
import tempfile
from mini_harness.config import load_config

def test_load_yaml_config():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
        tmp.write("input:\n  - data.csv\noutput: out\nmemory: mem.md\n")
        tmp_path = tmp.name
    try:
        config = load_config(tmp_path)
        assert config['input'] == ['data.csv']
        assert config['output'] == 'out'
        assert config['memory'] == 'mem.md'
    finally:
        os.unlink(tmp_path)

def test_load_json_config():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        json.dump({'input': ['data.csv'], 'output': 'out', 'memory': 'mem.md'}, tmp)
        tmp_path = tmp.name
    try:
        config = load_config(tmp_path)
        assert config['input'] == ['data.csv']
        assert config['output'] == 'out'
        assert config['memory'] == 'mem.md'
    finally:
        os.unlink(tmp_path)

def test_missing_config():
    try:
        load_config('nonexistent.yaml')
        assert False, "Should have raised"
    except FileNotFoundError:
        pass

def test_unsupported_extension():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write("data")
        tmp_path = tmp.name
    try:
        try:
            load_config(tmp_path)
            assert False, "Should have raised"
        except ValueError as e:
            assert 'Unsupported config format' in str(e)
    finally:
        os.unlink(tmp_path)
