"""Core DAG runner for the mini data harness."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class HarnessResult:
    records: list[dict[str, Any]]
    rejects: list[dict[str, Any]]
    report: dict[str, Any]
    logs: list[dict[str, Any]]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_from_root(path: str | Path, root: Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (root or repo_root()) / candidate


def snake_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value.strip())
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    return value.strip("_").lower()


def extract_records(paths: Iterable[str | Path], root: Path | None = None) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    base = root or repo_root()
    for raw_path in paths:
        path = resolve_from_root(raw_path, base)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            extracted.extend(_read_csv(path, base))
        elif suffix == ".jsonl":
            extracted.extend(_read_jsonl(path, base))
        else:
            raise ValueError(f"unsupported input type: {path}")
    return extracted


def clean_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cleaned: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        normalized = {
            snake_case(str(key)): value.strip() if isinstance(value, str) else value
            for key, value in record.items()
        }
        if _is_empty_record(normalized):
            continue
        if not str(normalized.get("id", "")).strip():
            rejects.append(
                {
                    "reason": "missing_id",
                    "record_index": index,
                    "record": normalized,
                    "source_file": record.get("_source_file"),
                }
            )
            continue
        cleaned.append(normalized)
    return cleaned, rejects


def build_report(
    records: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    retry_count: int,
    source_files: Iterable[str],
) -> dict[str, Any]:
    return {
        "processed_count": len(records),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": list(source_files),
    }


def run_dag(
    input_paths: Iterable[str | Path],
    *,
    max_retries: int = 2,
    root: Path | None = None,
) -> HarnessResult:
    base = root or repo_root()
    resolved_inputs = [resolve_from_root(path, base) for path in input_paths]
    logs: list[dict[str, Any]] = []
    retry_count = 0

    extracted, retries = _run_stage(
        "extract",
        lambda: extract_records(resolved_inputs, base),
        logs,
        max_retries,
    )
    retry_count += retries

    cleaned_result, retries = _run_stage(
        "clean",
        lambda: clean_records(extracted),
        logs,
        max_retries,
    )
    retry_count += retries
    records, rejects = cleaned_result

    source_files = [_relative_or_absolute(path, base) for path in resolved_inputs]
    report, retries = _run_stage(
        "report",
        lambda: build_report(records, rejects, retry_count, source_files),
        logs,
        max_retries,
    )
    retry_count += retries
    report["retry_count"] = retry_count

    return HarnessResult(records=records, rejects=rejects, report=report, logs=logs)


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    target = Path(path)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _run_stage(
    stage: str,
    func: Callable[[], Any],
    logs: list[dict[str, Any]],
    max_retries: int,
) -> tuple[Any, int]:
    retry_count = 0
    for attempt in range(1, max_retries + 2):
        try:
            result = func()
        except Exception as exc:
            status = "retrying" if attempt <= max_retries else "failed"
            logs.append(
                {
                    "attempt": attempt,
                    "stage": stage,
                    "status": status,
                    "error": str(exc),
                }
            )
            if attempt > max_retries:
                raise
            retry_count += 1
        else:
            logs.append({"attempt": attempt, "stage": stage, "status": "ok"})
            return result, retry_count
    raise RuntimeError(f"stage did not complete: {stage}")


def _read_csv(path: Path, root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        filtered_lines = [
            line
            for line in handle
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if not filtered_lines:
        return rows
    reader = csv.DictReader(filtered_lines)
    for row in reader:
        if _is_empty_record(row):
            continue
        row["_source_file"] = _relative_or_absolute(path, root)
        rows.append(row)
    return rows


def _read_jsonl(path: Path, root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            value["_source_file"] = _relative_or_absolute(path, root)
            rows.append(value)
    return rows


def _is_empty_record(record: dict[str, Any]) -> bool:
    return all(not str(value).strip() for value in record.values())


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
