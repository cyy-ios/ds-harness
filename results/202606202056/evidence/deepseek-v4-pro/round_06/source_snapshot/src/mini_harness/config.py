"""Configuration loading for mini_harness."""
import json
import os
import re
from typing import Any, Dict

def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from JSON or YAML file. If no path given, return defaults."""
    defaults = {
        "input_files": [],
        "max_retries": 2,
        "log_level": "INFO"
    }
    if not config_path:
        return defaults
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    _, ext = os.path.splitext(config_path)
    if ext == '.json':
        with open(config_path, encoding='utf-8') as f:
            data = json.load(f)
    elif ext in ('.yml', '.yaml'):
        data = parse_yaml(config_path)
    else:
        raise ValueError(f"Unsupported config format: {ext}")
    # Merge with defaults
    config = defaults.copy()
    config.update(data)
    return config

def parse_yaml(file_path: str) -> dict:
    """Simple YAML parser for flat key-value mapping only."""
    result = {}
    with open(file_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Support key: value
            match = re.match(r'^([\w_-]+)\s*:\s*(.*)$', line)
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            # Remove surrounding quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            # Try to convert to number or boolean
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
            result[key] = value
    return result
