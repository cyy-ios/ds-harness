import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from JSON file.
    If config_path is provided, use it; otherwise look for 'harness.json' in current directory.
    If file not found, return empty dict.
    Raise ValueError for unsupported file extensions (e.g., .yaml/.yml).
    """
    if config_path is None:
        default_path = Path("harness.json")
        if default_path.exists():
            config_path = str(default_path)
        else:
            return {}
    
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    ext = path.suffix.lower()
    if ext == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif ext in ('.yaml', '.yml'):
        raise ValueError("YAML configuration support requires PyYAML. Please use JSON format or install PyYAML.")
    else:
        raise ValueError(f"Unsupported config file format: {ext}. Use JSON.")
