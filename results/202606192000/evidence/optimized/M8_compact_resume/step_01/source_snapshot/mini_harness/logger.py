"""Structured logger: each log line must contain attempt, stage, status."""
import json
import sys
import time


def log(attempt: int, stage: str, status: str, **extra) -> None:
    """Write a single JSON log line to stderr."""
    record = {
        "attempt": attempt,
        "stage": stage,
        "status": status,
        "timestamp": time.time(),
    }
    record.update(extra)
    sys.stderr.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stderr.flush()

