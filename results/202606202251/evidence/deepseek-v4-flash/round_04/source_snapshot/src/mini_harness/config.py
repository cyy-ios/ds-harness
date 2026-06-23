import json
from pathlib import Path

def load_config(config_path):
    """Load config from JSON or YAML file."""
    ext = Path(config_path).suffix.lower()
    if ext == '.json':
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif ext in ('.yaml', '.yml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            return parse_yaml(f.read())
    else:
        raise ValueError(f'Unsupported config format: {ext}')

def parse_yaml(text):
    """Simple YAML parser for flat key-value pairs (no nesting)."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            # Handle quoted strings
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            # Try to parse int/float
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
            result[key] = val
    return result
