import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "output": "report.json",
    "max_retries": 2,
    "log_level": "INFO"
}


class Config:
    def __init__(self, values=None):
        self.values = DEFAULT_CONFIG.copy()
        if values:
            self.values.update(values)

    @classmethod
    def from_file(cls, file_path):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        if path.suffix in ('.json',):
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        elif path.suffix in ('.yaml', '.yml'):
            data = load_yaml(path)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
        # ensure data is a dict
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a dictionary.")
        return cls(data)

    def __getattr__(self, name):
        # Fallback to dict keys
        if name in self.values:
            return self.values[name]
        raise AttributeError(f"Config has no attribute '{name}'")

    def get(self, key, default=None):
        return self.values.get(key, default)


def load_yaml(path):
    """
    Minimal YAML loader supporting flat key-value pairs and simple lists.
    No nesting, no anchors, no tags.
    """
    result = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if ':' not in stripped:
                continue  # skip lines without key-value
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()
            # unquote
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            # Try numeric
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.lower() == 'null' or value == '':
                value = None
            else:
                # Check for list (e.g., [item1, item2])
                if value.startswith('[') and value.endswith(']'):
                    items = value[1:-1].split(',')
                    value = [parse_yaml_value(item.strip()) for item in items if item.strip()]
                else:
                    value = parse_yaml_value(value)
            result[key] = value
    return result


def parse_yaml_value(value):
    # unquote
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    # int/float
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass
    # boolean/null
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    if value.lower() == 'null':
        return None
    return value
