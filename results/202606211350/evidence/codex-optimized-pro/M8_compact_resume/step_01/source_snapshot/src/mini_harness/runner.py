"""DAG runner for the mini data processing harness.

Exposes ``run_dag`` (entry point) and ``HarnessError`` (exception class).
"""

import csv
import json
import re
import time
from pathlib import Path

from mini_harness.config import REPO_ROOT, load_config, _resolve_path
from mini_harness.report import generate_report

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class HarnessError(Exception):
    """Raised when a DAG stage fails irrecoverably."""
    def __init__(self, stage: str, message: str):
        super().__init__(f"[{stage}] {message}")
        self.stage = stage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_snake_case(name: str) -> str:
    """Convert arbitrary field name to snake_case."""
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"[-\s]+", "_", s)
    return s.lower().strip("_")


def _resolve_repo_path(raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def _extract(source_paths: list[str]) -> list[dict]:
    """Read CSV and JSONL files, return raw records (dicts with original keys)."""
    rows: list[dict] = []
    for sp in source_paths:
        fpath = _resolve_repo_path(sp)
        if not fpath.is_file():
            raise HarnessError("extract", f"file not found: {fpath}")
        if fpath.suffix.lower() == ".csv":
            rows.extend(_read_csv(fpath))
        elif fpath.suffix.lower() in (".jsonl", ".jsonl"):
            rows.extend(_read_jsonl(fpath))
        else:
            raise HarnessError("extract", f"unsupported format: {fpath.suffix}")
    return rows


def _read_csv(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        # Filter out comment lines (starting with #) before parsing
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    import io
    reader = csv.DictReader(io.StringIO("".join(lines)))
    for row in reader:
        stripped = {}
        for k, v in row.items():
            if k is None:
                continue
            key = k.strip()
            val = v.strip() if isinstance(v, str) else v
            stripped[key] = val
        # Drop fully empty rows
        if any(v for v in stripped.values()):
            out.append(stripped)
    return out


def _read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
    return records


def _clean(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Apply cleaning rules; return (clean_records, rejects)."""
    clean_rows: list[dict] = []
    rejects: list[dict] = []
    for rec in records:
        # Normalise keys to snake_case
        norm = {_to_snake_case(k): v for k, v in rec.items()}
        # Missing `id` -> reject
        if "id" not in norm or norm["id"] is None or str(norm["id"]).strip() == "":
            rejects.append(norm)
        else:
            clean_rows.append(norm)
    return clean_rows, rejects


# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

def _run_stage_with_retry(stage: str, fn, retry_max: int, log_dir: Path, **kwargs):
    """Execute *fn* up to 1 + retry_max times, logging each attempt."""
    log_dir.mkdir(parents=True, exist_ok=True)
    last_exc: Exception | None = None
    for attempt in range(1, 1 + retry_max + 1):
        entry = {"attempt": attempt, "stage": stage, "status": "started"}
        try:
            result = fn(**kwargs)
            entry["status"] = "ok"
            _write_log(log_dir, entry)
            return result
        except Exception as exc:
            entry["status"] = "failed"
            _write_log(log_dir, entry)
            last_exc = exc
            if attempt <= retry_max:
                time.sleep(0.05 * attempt)
    raise HarnessError(stage, str(last_exc)) from last_exc


def _write_log(log_dir: Path, entry: dict):
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    fname = f"harness_{ts}.jsonl"
    with (log_dir / fname).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_dag(source_files: list[str], output: str, config_path: str | None = None) -> dict:
    """Execute the full DAG: extract -> clean -> report.

    Returns the report dict.
    """
    cfg = load_config(config_path)
    log_dir = _resolve_repo_path(cfg["log_dir"])
    retry_max = cfg["retry_max"]

    raw = _run_stage_with_retry("extract", _extract, retry_max, log_dir,
                                source_paths=source_files)
    clean_rows, rejects = _run_stage_with_retry("clean", _clean, retry_max, log_dir,
                                                records=raw)
    report = generate_report(
        clean=clean_rows,
        rejects=rejects,
        retry_count=0,
        source_files=source_files,
        output_path=output,
    )
    return report
