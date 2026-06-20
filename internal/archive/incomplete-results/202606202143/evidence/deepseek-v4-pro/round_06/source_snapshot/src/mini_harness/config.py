import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def load_config(config_path: Path) -> dict:
    """
    Load configuration from a JSON or YAML file.
    Returns a dict. Raises ValueError for unsupported formats.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Try JSON first
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        if yaml is not None:
            try:
                result = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Failed to parse config as JSON or YAML: {e}")
        else:
            raise ValueError("Config file is not valid JSON and PyYAML is not installed")
    if not isinstance(result, dict):
        raise ValueError(f"Failed to parse config as JSON or YAML: expected a mapping, got {type(result).__name__}")
    return result
