"""Extract stage: read CSV or JSONL into list of dicts."""

import csv
import json
from pathlib import Path


def extract(input_path):
    ext = Path(input_path).suffix.lower()
    if ext == ".csv":
        return _read_csv(input_path)
    elif ext == ".jsonl":
        return _read_jsonl(input_path)
    raise ValueError(f"Unsupported input format: {ext}")


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _read_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records
