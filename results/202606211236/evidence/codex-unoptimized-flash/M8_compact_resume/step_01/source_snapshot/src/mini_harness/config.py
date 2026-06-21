"""JSON and minimal YAML config loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runner import HarnessError, REPO_ROOT, _repo_path


DEFAULT_CONFIG_NAMES = ("harness.json", "harness.yaml", "harness.yml")


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load an explicit config path or the first repo-root default config."""

    config_path = _find_config(path)
    if config_path is None:
        return {}

    suffix = config_path.suffix.lower()
    text = config_path.read_text(encoding="utf-8")
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HarnessError(f"invalid JSON config: {config_path.name}") from exc
    elif suffix in {".yaml", ".yml"}:
        data = _parse_simple_yaml(text)
    else:
        raise HarnessError(f"unsupported config type: {config_path.suffix}")

    if not isinstance(data, dict):
        raise HarnessError("config root must be an object")
    return data


def resolve_run_settings(
    cli_sources: list[str],
    cli_output: str | None,
    config_path: str | None,
) -> tuple[list[str], str, str | None]:
    config = load_config(config_path)
    sources = cli_sources or _string_list(config.get("sources", []), "sources")
    output = cli_output or _optional_string(config.get("output"), "output")

    if not sources:
        raise HarnessError("sources are required via CLI args or config")
    if not output:
        raise HarnessError("output is required via --output or config")

    loaded_path = _find_config(config_path)
    loaded_display = loaded_path.relative_to(REPO_ROOT).as_posix() if loaded_path else None
    return sources, output, loaded_display


def _find_config(path: str | None) -> Path | None:
    if path:
        config_path = _repo_path(path)
        if not config_path.exists():
            raise HarnessError(f"config does not exist: {path}")
        return config_path

    for name in DEFAULT_CONFIG_NAMES:
        config_path = REPO_ROOT / name
        if config_path.exists():
            return config_path
    return None


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise HarnessError(f"config {name} must be a list of strings")
    return value


def _optional_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise HarnessError(f"config {name} must be a string")
    return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_list: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            if current_list is None:
                raise HarnessError("YAML list item without key")
            result[current_list].append(_yaml_scalar(stripped[2:].strip()))
            continue

        current_list = None
        if ":" not in stripped:
            raise HarnessError(f"invalid YAML line: {raw_line}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise HarnessError("YAML key cannot be empty")
        if raw_value == "":
            result[key] = []
            current_list = key
        else:
            result[key] = _yaml_scalar(raw_value)

    return result


def _yaml_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(part.strip()) for part in inner.split(",")]
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value
