"""Extract stage: read CSV or JSONL into list of dicts."""

import csv
import io
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
    with open(path, encoding="utf-8-sig") as f:
        raw_lines = f.readlines()
    lines = [ln for ln in raw_lines if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return []
    return [dict(row) for row in csv.DictReader(io.StringIO("".join(lines)))]


def _read_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records
