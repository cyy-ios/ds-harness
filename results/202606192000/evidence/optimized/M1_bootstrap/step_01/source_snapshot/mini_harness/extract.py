"""extract 阶段：读取 CSV / JSONL 文件，返回记录列表。"""
import csv
import json
from pathlib import Path
from typing import Any, List

from mini_harness.retry import with_retry


@with_retry(stage="extract")
def extract(source: Path) -> List[dict[str, Any]]:
    """从 CSV 或 JSONL 文件提取全部记录。"""
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return _read_csv(source)
    if suffix == ".jsonl":
        return _read_jsonl(source)
    raise ValueError(f"不支持的文件类型: {suffix}")


def _read_csv(path: Path) -> List[dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _read_jsonl(path: Path) -> List[dict[str, Any]]:
    records: List[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
