"""DAG runner for the fixture data harness."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Callable

from .report import STAGES, build_report, display_path, write_report

MAX_RETRIES = 2


class HarnessError(Exception):
    """Raised when the harness cannot complete a run."""


def run_dag(
    source_files: list[str] | tuple[str, ...],
    output: str,
    *,
    repo_root: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run extract, clean, and report stages and write a JSON report."""

    root = _repo_root(repo_root)
    sources = [_resolve_under_root(root, source) for source in source_files]
    output_path = _resolve_under_root(root, output)

    state: dict[str, Any] = {
        "root": root,
        "sources": sources,
        "output": output_path,
        "logs": [],
        "retry_count": 0,
        "config": dict(config or {}),
    }

    for stage_name, stage_func in (
        ("extract", _extract),
        ("clean", _clean),
        ("report", _report),
    ):
        _run_stage(stage_name, stage_func, state)

    return state["report"]


def _run_stage(stage: str, func: Callable[[dict[str, Any]], None], state: dict[str, Any]) -> None:
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            func(state)
        except Exception as exc:  # noqa: BLE001 - converts all stage failures into HarnessError.
            state["logs"].append({"attempt": attempt, "stage": stage, "status": "failed", "error": str(exc)})
            if attempt <= MAX_RETRIES:
                state["retry_count"] += 1
                continue
            if isinstance(exc, HarnessError):
                raise
            raise HarnessError(f"{stage} failed after {attempt} attempts: {exc}") from exc
        state["logs"].append(_success_log(attempt, stage, state))
        if stage == "report":
            _write_report(state)
        return


def _success_log(attempt: int, stage: str, state: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {"attempt": attempt, "stage": stage, "status": "ok"}
    if stage == "extract":
        entry["record_count"] = len(state.get("raw_records", []))
    elif stage == "clean":
        entry["processed_count"] = len(state.get("cleaned_records", []))
        entry["rejected_count"] = len(state.get("rejects", []))
    elif stage == "report":
        entry["output"] = display_path(state["root"], state["output"])
    return entry


def _extract(state: dict[str, Any]) -> None:
    records: list[dict[str, Any]] = []
    for source in state["sources"]:
        if not source.exists():
            raise HarnessError(f"source file not found: {display_path(state['root'], source)}")
        suffix = source.suffix.lower()
        if suffix == ".csv":
            records.extend(_read_csv(source))
        elif suffix == ".jsonl":
            records.extend(_read_jsonl(source))
        else:
            raise HarnessError(f"unsupported input format: {source.suffix or source.name}")
    state["raw_records"] = records


def _clean(state: dict[str, Any]) -> None:
    cleaned: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []

    for record in state.get("raw_records", []):
        normalized = {_snake_case(str(key)): value for key, value in record.items()}
        if _is_empty_record(normalized):
            continue
        if not str(normalized.get("id", "")).strip():
            rejects.append({"record": normalized, "reason": "missing id"})
            continue
        cleaned.append(normalized)

    state["cleaned_records"] = cleaned
    state["rejects"] = rejects


def _report(state: dict[str, Any]) -> None:
    state["report"] = build_report(state)
    _write_report(state)


def _write_report(state: dict[str, Any]) -> None:
    write_report(state["report"], state["output"])


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as source:
        filtered = [line for line in source if line.strip() and not line.lstrip().startswith("#")]
    with io.StringIO("".join(filtered), newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise HarnessError(f"{path.name}:{line_number} is not a JSON object")
            records.append(value)
    return records


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()

    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").exists() and (candidate / "skills" / "data-harness" / "SKILL.md").exists():
            return candidate
    raise HarnessError("could not locate repo root")


run_dag.repo_root = _repo_root  # type: ignore[attr-defined]


def _resolve_under_root(root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HarnessError(f"path escapes repo root: {value}") from exc
    return resolved


def _snake_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value.strip())
    value = re.sub(r"[^0-9A-Za-z]+", "_", value.strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value.lower()


def _is_empty_record(record: dict[str, Any]) -> bool:
    return all(value is None or str(value).strip() == "" for value in record.values())
