"""Pipeline DAG: extract -> clean -> report with retry and logging."""

import json
from pathlib import Path
from datetime import datetime, timezone
from mini_harness.extract import extract
from mini_harness.clean import clean
from mini_harness.report import write_report

MAX_RETRIES = 2


def _log(attempt, stage, status, repo_root, detail=None):
    logs_dir = Path(repo_root) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attempt": attempt,
        "stage": stage,
        "status": status,
    }
    if detail:
        entry["detail"] = detail
    log_path = logs_dir / "pipeline.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _retry_wrapper(fn, stage, repo_root):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            result = fn()
            _log(attempt, stage, "success", repo_root)
            return result
        except Exception as e:
            last_err = e
            _log(attempt, stage, "failure", repo_root, {"error": str(e)})
    _log(MAX_RETRIES + 1, stage, "exhausted", repo_root, {"error": str(last_err)})
    raise RuntimeError(f"Stage '{stage}' failed after {MAX_RETRIES} retries") from last_err


def run_pipeline(input_path, repo_root):
    retry_count = 0

    def do_extract():
        return extract(input_path)

    records = _retry_wrapper(do_extract, "extract", repo_root)

    def do_clean():
        return clean(records)

    processed, rejected = _retry_wrapper(do_clean, "clean", repo_root)

    source_files = [input_path]

    def do_report():
        return write_report(
            processed_count=len(processed),
            rejected_count=len(rejected),
            retry_count=retry_count,
            source_files=source_files,
            repo_root=repo_root,
        )

    _retry_wrapper(do_report, "report", repo_root)
