"""Configuration loader for mini_harness. Supports JSON and YAML config files.

Uses only the standard library. YAML parsing covers flat key-value pairs
and shallow nested maps (one level) to avoid third-party dependencies.
"""

import json
import os
from pathlib import Path


def _resolve_repo_root() -> Path:
    """Walk upward from this file to find the repo root (contains pyproject.toml)."""
    candidate = Path(__file__).resolve().parent
    for _ in range(10):
        if (candidate / "pyproject.toml").is_file():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return Path.cwd()


REPO_ROOT = _resolve_repo_root()

DEFAULTS = {
    "retry_max": 2,
    "log_dir": "logs",
    "output_dir": "tmp",
    "encoding": "utf-8",
}


def _parse_yaml(text: str) -> dict:
    """Minimal YAML parser for flat and one-level nested key-value pairs.

    Supports: scalars, bools, ints, floats, null/None, simple nesting.
    Does *not* support: lists, anchors, aliases, multi-level nesting.
    """
    result = {}
    stack = [(result, -1)]
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        content = line.strip()
        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip()

        # Unwind stack to current indent level
        while stack and indent <= stack[-1][1]:
            stack.pop()
        current_map = stack[-1][0] if stack else result

        if value == "":
            # Nested map indicator
            nested = {}
            current_map[key] = nested
            stack.append((nested, indent))
        else:
            current_map[key] = _coerce_yaml_value(value)
    return result


def _coerce_yaml_value(raw: str) -> object:
    raw = raw.strip().strip('"').strip("'")
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if raw.lower() in ("null", "~", "none"):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def load_config(explicit_path: str | None = None) -> dict:
    """Load configuration, merging built-in defaults with a config file.

    If *explicit_path* is given, that file is used. Otherwise we probe, in
    order: `config.yaml`, `config.json` at repo root.
    Returns a merged dict (defaults overridden by file values).
    """
    merged = dict(DEFAULTS)

    if explicit_path:
        cfg_path = _resolve_path(explicit_path)
    else:
        cfg_path = None
        for name in ("config.yaml", "config.json"):
            candidate = REPO_ROOT / name
            if candidate.is_file():
                cfg_path = candidate
                break

    if cfg_path is None or not cfg_path.is_file():
        return merged

    text = cfg_path.read_text(encoding='utf-8-sig')
    if cfg_path.suffix.lower() in (".json",):
        file_cfg = json.loads(text)
    else:
        file_cfg = _parse_yaml(text)

    merged.update(file_cfg)
    return merged


def _resolve_path(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return REPO_ROOT / p

