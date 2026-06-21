"""Configuration loading for the mini harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import HarnessError


DEFAULT_CONFIG_NAMES = ("harness.json", "harness.yaml", "harness.yml")


def load_config(repo_root: Path, config_path: str | Path | None) -> dict[str, Any]:
    path = _config_path(repo_root, config_path)
    if path is None:
        return {}
    if not path.exists():
        raise HarnessError(f"config does not exist: {_relative_to_root(repo_root, path)}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HarnessError(f"invalid JSON config: {_relative_to_root(repo_root, path)}") from exc
    elif suffix in {".yaml", ".yml"}:
        value = _parse_simple_yaml(text)
    else:
        raise HarnessError(f"unsupported config type: {path.suffix}")
    if not isinstance(value, dict):
        raise HarnessError("config root must be an object")
    return value


def _config_path(repo_root: Path, config_path: str | Path | None) -> Path | None:
    if config_path is not None:
        path = Path(config_path)
        return path.resolve() if path.is_absolute() else (repo_root / path).resolve()
    for name in DEFAULT_CONFIG_NAMES:
        candidate = repo_root / name
        if candidate.exists():
            return candidate
    return None


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_list is None:
                raise HarnessError("YAML list item without a key")
            current_list.append(_parse_scalar(stripped[2:].strip()))
            continue
        if ":" not in stripped:
            raise HarnessError(f"invalid YAML line: {raw_line}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise HarnessError(f"invalid YAML key: {raw_line}")
        if raw_value == "":
            current_key = key
            current_list = []
            result[current_key] = current_list
        else:
            current_key = None
            current_list = None
            result[key] = _parse_scalar(raw_value)

    return result


def _parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    return value


def _relative_to_root(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()
