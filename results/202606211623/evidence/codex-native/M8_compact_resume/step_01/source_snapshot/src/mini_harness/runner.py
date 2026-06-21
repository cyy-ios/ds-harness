"""Minimal CSV/JSONL DAG runner."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


class HarnessError(Exception):
    """Raised when the harness cannot complete the DAG."""


@dataclass
class DagState:
    source_files: list[str]
    raw_records: list[dict[str, Any]]
    clean_records: list[dict[str, Any]]
    rejects: list[dict[str, Any]]
    logs: list[dict[str, Any]]
    retry_count: int = 0


def run_dag(
    sources: Iterable[str | Path] | None = None,
    output: str | Path | None = None,
    config: str | Path | None = None,
) -> dict[str, Any]:
    """Run extract, clean, and report stages and write the JSON report."""

    repo_root = _repo_root()
    harness_config = _load_config(repo_root, config)
    source_values = list(sources or []) or _config_sources(harness_config)
    output_value = output or harness_config.get("output")
    if not source_values:
        raise HarnessError("at least one source is required")
    if not output_value:
        raise HarnessError("output is required")

    source_paths = [_resolve_repo_path(repo_root, source) for source in source_values]
    output_path = _resolve_repo_path(repo_root, output_value)
    state = DagState(
        source_files=[_relative_to_root(repo_root, path) for path in source_paths],
        raw_records=[],
        clean_records=[],
        rejects=[],
        logs=[],
    )

    for stage, func in (
        ("extract", lambda: _extract(source_paths, state)),
        ("clean", lambda: _clean(state)),
    ):
        _run_stage(stage, func, state)

    _run_report_stage(repo_root, output_path, state)
    return json.loads(output_path.read_text(encoding="utf-8"))


def _run_stage(stage: str, func: Callable[[], None], state: DagState) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - converted to HarnessError below.
            last_error = exc
            state.logs.append(_log_entry(attempt, stage, "failed", exc))
            if attempt < 3:
                state.retry_count += 1
                continue
            break
        state.logs.append(_log_entry(attempt, stage, "succeeded"))
        return
    raise HarnessError(f"stage {stage!r} failed after 3 attempts: {last_error}")


def _run_report_stage(repo_root: Path, output_path: Path, state: DagState) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        success_log = {"attempt": attempt, "stage": "report", "status": "succeeded"}
        try:
            _report(repo_root, output_path, state, success_log=success_log)
        except Exception as exc:  # noqa: BLE001 - converted to HarnessError below.
            last_error = exc
            state.logs.append(_log_entry(attempt, "report", "failed", exc))
            if attempt < 3:
                state.retry_count += 1
                continue
            break
        state.logs.append(success_log)
        return
    raise HarnessError(f"stage 'report' failed after 3 attempts: {last_error}")


def _extract(source_paths: list[Path], state: DagState) -> None:
    records: list[dict[str, Any]] = []
    for path in source_paths:
        if not path.exists():
            raise HarnessError(f"source does not exist: {_relative_to_root(_repo_root(), path)}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            records.extend(_read_csv(path))
        elif suffix == ".jsonl":
            records.extend(_read_jsonl(path))
        else:
            raise HarnessError(f"unsupported source type: {path.suffix}")
    state.raw_records = records


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        data_lines = (line for line in handle if _is_data_line(line))
        return [dict(row) for row in csv.DictReader(data_lines) if _has_values(row.values())]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HarnessError(f"invalid JSONL at {path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise HarnessError(f"JSONL record must be an object at {path}:{line_number}")
            records.append(value)
    return records


def _clean(state: DagState) -> None:
    clean_records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []

    for index, record in enumerate(state.raw_records):
        cleaned = {_snake_case(str(key)): value for key, value in record.items()}
        if not str(cleaned.get("id", "")).strip():
            rejects.append({"index": index, "reason": "missing_id", "record": cleaned})
            continue
        clean_records.append(cleaned)

    state.clean_records = clean_records
    state.rejects = rejects


def _report(
    repo_root: Path,
    output_path: Path,
    state: DagState,
    success_log: dict[str, Any] | None = None,
) -> None:
    from .report import build_report, write_report

    logs = [*state.logs]
    if success_log is not None:
        logs.append(success_log)
    report = build_report(
        processed_records=state.clean_records,
        rejects=state.rejects,
        retry_count=state.retry_count,
        source_files=state.source_files,
        logs=logs,
    )
    write_report(output_path, report)


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for path in (current, *current.parents):
        if (path / "pyproject.toml").exists() and (path / "AGENTS.md").exists():
            return path
    raise HarnessError("could not locate repository root")


def _resolve_repo_path(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _relative_to_root(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _has_values(values: Iterable[Any]) -> bool:
    return any(str(value or "").strip() for value in values)


def _is_data_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _log_entry(
    attempt: int,
    stage: str,
    status: str,
    error: Exception | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {"attempt": attempt, "stage": stage, "status": status}
    if error is not None:
        entry["error"] = str(error)
    return entry


def _snake_case(value: str) -> str:
    value = value.strip()
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def _load_config(repo_root: Path, config: str | Path | None) -> dict[str, Any]:
    from .config import load_config

    return load_config(repo_root, config)


def _config_sources(config: dict[str, Any]) -> list[str | Path]:
    value = config.get("sources", config.get("source_files", []))
    if isinstance(value, (str, Path)):
        return [value]
    if isinstance(value, list) and all(isinstance(item, (str, Path)) for item in value):
        return value
    if value:
        raise HarnessError("config sources must be a string or list of strings")
    return []
