from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
from typing import Any

from .cleaning import clean_records

MAX_RETRIES = 2

class Stage:
    def __init__(self, name: str):
        self.name = name
        self.attempt = 0
        self.status = "pending"

class Runner:
    def __init__(self, input_files: list[str]):
        self.input_files = input_files
        self.logs: list[dict] = []
        self.retry_count = 0
        self.extract_stage = Stage("extract")
        self.clean_stage = Stage("clean")
        self.report_stage = Stage("report")

    def _log(self, stage: str, attempt: int, status: str, message: str = ""):
        entry = {"stage": stage, "attempt": attempt, "status": status, "message": message}
        self.logs.append(entry)

    def _run_with_retry(self, stage: Stage, func, *args, **kwargs):
        for attempt in range(1, MAX_RETRIES + 2):  # 1 initial + max_retries
            stage.attempt = attempt
            try:
                result = func(*args, **kwargs)
                stage.status = "success"
                self._log(stage.name, attempt, "success")
                return result
            except Exception as e:
                stage.status = "failure"
                self._log(stage.name, attempt, "failure", str(e))
                if attempt >= MAX_RETRIES + 1:
                    raise  # exhausted retries
                self.retry_count += 1
                # retry
                continue
        raise RuntimeError("Unexpected: retry loop ended without success or exception")

    def extract(self) -> list[dict]:
        """Load records from input files."""
        all_records = []
        for file_str in self.input_files:
            path = Path(file_str)
            if not path.is_absolute():
                path = Path.cwd() / path
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            ext = path.suffix.lower()
            if ext == '.csv':
                with open(path, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        all_records.append(row)
            elif ext in ('.jsonl', '.json'):
                with open(path, encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        all_records.append(json.loads(line))
            else:
                raise ValueError(f"Unsupported file type: {ext}")
        return all_records

    def clean(self, raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
        """Clean records."""
        return clean_records(raw_records)

    def report(self, processed: list[dict], rejected: list[dict]) -> dict:
        """Generate report."""
        return {
            "processed_count": len(processed),
            "rejected_count": len(rejected),
            "retry_count": self.retry_count,
            "source_files": self.input_files,
        }

    def run(self) -> dict:
        """Execute DAG: extract -> clean -> report, with retries."""
        # Extract
        raw_records = self._run_with_retry(self.extract_stage, self.extract)
        # Clean
        processed, rejected = self._run_with_retry(self.clean_stage, self.clean, raw_records)
        # Report
        report = self._run_with_retry(self.report_stage, self.report, processed, rejected)
        return report
