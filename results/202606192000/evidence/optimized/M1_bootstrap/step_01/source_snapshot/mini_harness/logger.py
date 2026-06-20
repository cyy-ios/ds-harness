"""结构化日志：每条日志必须包含 attempt, stage, status。"""
import json
import sys
import time


def log(attempt: int, stage: str, status: str, **extra) -> None:
    """写入一条 JSON 行日志到 stdout。"""
    record = {
        "attempt": attempt,
        "stage": stage,
        "status": status,
        "timestamp": time.time(),
    }
    record.update(extra)
    sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stdout.flush()
