import os
import json

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DEFAULT_CONFIG_NAMES = ["harness_config.json", "harness_config.yaml", "harness_config.yml"]

class Config:
    @staticmethod
    def load(config_path=None):
        """Load configuration from a file. If config_path provided, use it; otherwise search for default names in current directory."""
        if config_path:
            if not os.path.isfile(config_path):
                raise FileNotFoundError(f"Config file not found: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                return Config._parse(f, config_path)
        else:
            for name in DEFAULT_CONFIG_NAMES:
                if os.path.isfile(name):
                    with open(name, 'r', encoding='utf-8') as f:
                        return Config._parse(f, name)
            # No default config found, return empty dict
            return {}

    @staticmethod
    def _parse(file, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.yaml', '.yml'):
            if not HAS_YAML:
                raise ImportError("PyYAML is required to parse YAML config")
            return yaml.safe_load(file)
        elif ext == '.json':
            return json.load(file)
        else:
            raise ValueError(f"Unsupported config file extension: {ext}")
