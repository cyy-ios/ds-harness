import json
from pathlib import Path

def load_config(filepath: str) -> dict:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")
    suffix = path.suffix.lower()
    if suffix in ('.yaml', '.yml'):
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    elif suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {suffix}")
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")
    return config

def find_default_config() -> dict | None:
    for name in ('harness_config.json', 'harness_config.yaml', 'harness_config.yml'):
        path = Path(name)
        if path.exists():
            return load_config(str(path))
    return None
