import json
import os

def load_config(path: str) -> dict:
    """Load configuration from JSON or YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "r") as f:
            return json.load(f)
    elif ext in (".yaml", ".yml"):
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported config file format: {ext}")
