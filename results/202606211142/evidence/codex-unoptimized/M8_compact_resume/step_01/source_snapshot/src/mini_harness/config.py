"""Configuration loading for mini_harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import HarnessError


DEFAULT_CONFIG_NAMES = ("mini_harness.json", "mini_harness.yaml", "mini_harness.yml")


def load_config(root: Path, config_path: str | None = None) -> dict[str, Any]:
    path = _find_config(root, config_path)
    if path is None:
        return {}

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        data = json.loads(text or "{}")
    elif suffix in {".yaml", ".yml"}:
        data = _parse_simple_yaml(text)
    else:
        raise HarnessError(f"unsupported config format: {path.suffix}")

    if not isinstance(data, dict):
        raise HarnessError("config must be a mapping")
    return data


def _find_config(root: Path, config_path: str | None) -> Path | None:
    if config_path is not None:
        path = Path(config_path)
        resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise HarnessError(f"config path escapes repo root: {config_path}") from exc
        if not resolved.exists():
            raise HarnessError(f"config file not found: {config_path}")
        return resolved

    for name in DEFAULT_CONFIG_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_key: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if line.startswith((" ", "\t")):
            stripped = line.strip()
            if current_key is None or not stripped.startswith("- "):
                raise HarnessError(f"unsupported YAML syntax on line {line_number}")
            result.setdefault(current_key, []).append(_parse_scalar(stripped[2:].strip()))
            continue

        if ":" not in line:
            raise HarnessError(f"unsupported YAML syntax on line {line_number}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise HarnessError(f"empty YAML key on line {line_number}")
        if value == "":
            result[key] = []
            current_key = key
        else:
            result[key] = _parse_scalar(value)
            current_key = None

    return result


def _parse_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    return value
