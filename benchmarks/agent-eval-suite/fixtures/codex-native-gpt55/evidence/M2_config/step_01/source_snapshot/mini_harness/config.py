"""Configuration loading for mini_harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runner import repo_root, resolve_from_root


DEFAULT_INPUTS = ["data/input.csv", "data/events.jsonl"]
DEFAULT_OUTPUT = "evidence/report.json"
DEFAULT_REJECTS_OUTPUT = "evidence/rejects.jsonl"
DEFAULT_LOG_OUTPUT = "logs/mini_harness.jsonl"
DEFAULT_MAX_RETRIES = 2
DEFAULT_CONFIG_NAMES = ("harness.json", "harness.yaml", "harness.yml")


@dataclass(frozen=True)
class HarnessConfig:
    inputs: list[str]
    output: str
    rejects_output: str
    log_output: str
    max_retries: int


def default_config() -> HarnessConfig:
    return HarnessConfig(
        inputs=list(DEFAULT_INPUTS),
        output=DEFAULT_OUTPUT,
        rejects_output=DEFAULT_REJECTS_OUTPUT,
        log_output=DEFAULT_LOG_OUTPUT,
        max_retries=DEFAULT_MAX_RETRIES,
    )


def load_config(path: str | Path | None = None, root: Path | None = None) -> HarnessConfig:
    base = root or repo_root()
    config_path = _find_config(path, base)
    if config_path is None:
        return default_config()

    raw = _load_mapping(config_path)
    defaults = default_config()
    return HarnessConfig(
        inputs=_string_list(raw.get("inputs", defaults.inputs), "inputs"),
        output=str(raw.get("output", defaults.output)),
        rejects_output=str(raw.get("rejects_output", defaults.rejects_output)),
        log_output=str(raw.get("log_output", defaults.log_output)),
        max_retries=int(raw.get("max_retries", defaults.max_retries)),
    )


def merge_config(
    config: HarnessConfig,
    *,
    inputs: list[str] | None = None,
    output: str | None = None,
    rejects_output: str | None = None,
    log_output: str | None = None,
    max_retries: int | None = None,
) -> HarnessConfig:
    return HarnessConfig(
        inputs=inputs if inputs is not None else config.inputs,
        output=output if output is not None else config.output,
        rejects_output=rejects_output if rejects_output is not None else config.rejects_output,
        log_output=log_output if log_output is not None else config.log_output,
        max_retries=max_retries if max_retries is not None else config.max_retries,
    )


def _find_config(path: str | Path | None, root: Path) -> Path | None:
    if path is not None:
        config_path = resolve_from_root(path, root)
        if not config_path.exists():
            raise FileNotFoundError(f"config file not found: {config_path}")
        return config_path

    for name in DEFAULT_CONFIG_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _load_mapping(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        value = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"unsupported config type: {path}")
    if not isinstance(value, dict):
        raise ValueError(f"config must be a mapping: {path}")
    return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list_key: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current_list_key is None:
                raise ValueError(f"YAML list item without key on line {line_number}")
            data[current_list_key].append(_parse_scalar(stripped[2:].strip()))
            continue
        if ":" not in stripped:
            raise ValueError(f"unsupported YAML syntax on line {line_number}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            raise ValueError(f"empty YAML key on line {line_number}")
        if raw_value:
            data[key] = _parse_scalar(raw_value)
            current_list_key = None
        else:
            data[key] = []
            current_list_key = key
    return data


def _parse_scalar(value: str) -> Any:
    value = _strip_quotes(value)
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _string_list(value: Any, field_name: str) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ValueError(f"{field_name} must be a string or list of strings")
