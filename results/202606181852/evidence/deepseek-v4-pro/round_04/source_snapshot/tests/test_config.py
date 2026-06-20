import json
from pathlib import Path
import tempfile
import yaml

def test_load_config_json():
    from mini_harness.config import load_config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"input": ["data/input.csv"], "max_retries": 3}, f)
    config = load_config(f.name)
    assert config == {"input": ["data/input.csv"], "max_retries": 3}
    Path(f.name).unlink()

def test_load_config_yaml():
    from mini_harness.config import load_config
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("input:\n  - data/input.csv\nmax_retries: 3\n")
    config = load_config(f.name)
    assert config == {"input": ["data/input.csv"], "max_retries": 3}
    Path(f.name).unlink()

def test_load_config_unsupported():
    from mini_harness.config import load_config
    import pytest
    # create a temporary file with unsupported extension
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("dummy")
    try:
        with pytest.raises(ValueError):
            load_config(f.name)
    finally:
        Path(f.name).unlink()

def test_find_default_config_missing():
    from mini_harness.config import find_default_config
    # expect None since no default config in temp dir
    assert find_default_config() is None

def test_find_default_config_present(tmp_path):
    from mini_harness.config import find_default_config
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    # create a default config file
    (tmp_path / "harness_config.json").write_text(json.dumps({"input": ["test.csv"]}))
    config = find_default_config()
    assert config == {"input": ["test.csv"]}
    os.chdir(old_cwd)
