"""DAG runner for the mini data harness."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Callable

from .report import build_report, write_report


class HarnessError(Exception):
    """Raised when the harness cannot complete the DAG."""


REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_RETRIES = 2


def run_dag(sources: list[str] | tuple[str, ...], output: str) -> dict[str, Any]:
    """Run extract, clean, and report stages and write a JSON report."""

    logs: list[dict[str, Any]] = []
    retry_count = 0

    def run_stage(name: str, func: Callable[[], Any]) -> Any:
        nonlocal retry_count
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                result = func()
            except Exception as exc:  # noqa: BLE001 - convert all stage failures.
                logs.append(
                    {
                        "attempt": attempt,
                        "stage": name,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                if attempt > MAX_RETRIES:
                    raise HarnessError(f"{name} failed after {attempt} attempts") from exc
                retry_count += 1
            else:
                logs.append({"attempt": attempt, "stage": name, "status": "ok"})
                return result
        raise HarnessError(f"{name} failed")

    source_paths = [_repo_path(source) for source in sources]
    output_path = _repo_path(output)
    records = run_stage("extract", lambda: _extract(source_paths))
    cleaned, rejects = run_stage("clean", lambda: _clean(records))
    return _run_report_stage(cleaned, rejects, retry_count, source_paths, logs, output_path)


def _run_report_stage(
    cleaned: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    retry_count: int,
    source_paths: list[Path],
    logs: list[dict[str, Any]],
    output_path: Path,
) -> dict[str, Any]:
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            success_log = {"attempt": attempt, "stage": "report", "status": "ok"}
            report = build_report(
                cleaned,
                rejects,
                retry_count,
                [_display_path(path) for path in source_paths],
                [*logs, success_log],
            )
            write_report(report, output_path)
        except Exception as exc:  # noqa: BLE001 - convert all report failures.
            logs.append(
                {
                    "attempt": attempt,
                    "stage": "report",
                    "status": "failed",
                    "error": str(exc),
                }
            )
            if attempt > MAX_RETRIES:
                raise HarnessError(f"report failed after {attempt} attempts") from exc
            retry_count += 1
        else:
            logs.append(success_log)
            return report
    raise HarnessError("report failed")


def _repo_path(path: str) -> Path:
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (REPO_ROOT / candidate).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise HarnessError(f"path is outside repo root: {path}") from exc
    return resolved


def _extract(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            raise HarnessError(f"source does not exist: {_display_path(path)}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            records.extend(_read_csv(path))
        elif suffix == ".jsonl":
            records.extend(_read_jsonl(path))
        else:
            raise HarnessError(f"unsupported source type: {_display_path(path)}")
    return records


def _read_csv(path: Path) -> list[dict[str, Any]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return [
        dict(row)
        for row in reader
        if row and any((value or "").strip() for value in row.values())
    ]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HarnessError(
                    f"invalid JSONL at {_display_path(path)}:{line_number}"
                ) from exc
            if not isinstance(value, dict):
                raise HarnessError(
                    f"JSONL record must be an object at {_display_path(path)}:{line_number}"
                )
            records.append(value)
    return records


def _clean(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cleaned: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    for record in records:
        normalized = {_snake_case(str(key)): value for key, value in record.items()}
        if not str(normalized.get("id", "")).strip():
            rejects.append(normalized)
        else:
            cleaned.append(normalized)
    return cleaned, rejects


def _snake_case(value: str) -> str:
    value = value.strip()
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    return value.strip("_").lower()


def _display_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()
