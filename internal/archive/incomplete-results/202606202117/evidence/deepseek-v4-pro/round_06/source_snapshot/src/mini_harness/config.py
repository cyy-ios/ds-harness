import json
import os
import yaml

def load_config(path):
    """Load configuration from a JSON or YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        if path.endswith('.yaml') or path.endswith('.yml'):
            return yaml.safe_load(f) or {}
        elif path.endswith('.json'):
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path}. Use .json, .yaml, or .yml")

def find_default_config():
    """Look for default config.yaml or config.json in the current working directory."""
    cwd = os.getcwd()
    for name in ['config.yaml', 'config.yml', 'config.json']:
        full = os.path.join(cwd, name)
        if os.path.exists(full):
            return full
    return None

def merge_config(cli_args, config_dict):
    """Merge CLI arguments into config dict: CLI overrides config."""
    # mapping from CLI arg names to config keys
    mapping = {
        'input': 'input',
        # later more
    }
    for arg_name, config_key in mapping.items():
        val = getattr(cli_args, arg_name, None)
        if val is not None:
            config_dict[config_key] = val
    return config_dict

DEFAULT_CONFIG = {
    'retry_count': 2,
    'stages': ['extract', 'clean', 'report']
}
