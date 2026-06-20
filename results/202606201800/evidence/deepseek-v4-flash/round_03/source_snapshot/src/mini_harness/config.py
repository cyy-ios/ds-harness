import json
from pathlib import Path

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    suffix = config_path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        # YAML not available; try JSON parse (may fail for native YAML)
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse YAML file {config_path}, using empty config.")
            return {}
    elif suffix == ".json":
        with open(config_path, "r") as f:
            return json.load(f)
    else:
        print(f"Warning: Unsupported config file format {suffix}, using empty config.")
        return {}
