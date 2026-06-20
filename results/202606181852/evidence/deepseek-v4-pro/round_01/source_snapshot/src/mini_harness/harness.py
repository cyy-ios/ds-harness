import csv
import json
import logging
import re
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


def snake_case(s: str) -> str:
    s = s.strip()
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    return s.lower().strip('_')


def parse_file(filepath: str) -> List[Dict]:
    if filepath.endswith('.csv'):
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                # skip empty rows
                if all(v is None or v.strip() == '' for v in row.values()):
                    continue
                rows.append(row)
            return rows
    elif filepath.endswith('.jsonl'):
        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    logger.error(f"invalid json line: {line[:50]}...")
                    continue
                rows.append(obj)
        return rows
    else:
        raise ValueError(f"Unsupported file type: {filepath}")


def extract(filepath: str) -> List[Dict]:
    return parse_file(filepath)


def clean_data(data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    cleaned = []
    rejected = []
    for rec in data:
        rec = {snake_case(k): v for k, v in rec.items()}
        if 'id' not in rec or not rec['id']:
            rejected.append(rec)
        else:
            cleaned.append(rec)
    return cleaned, rejected


def process_file(filepath: str, max_retries: int = 2) -> Tuple[List[Dict], List[Dict], int]:
    for attempt in range(1, max_retries + 2):
        try:
            logger.info(f"attempt={attempt}, stage=extract, status=started")
            raw = extract(filepath)
            logger.info(f"attempt={attempt}, stage=extract, status=completed")
            logger.info(f"attempt={attempt}, stage=clean, status=started")
            cleaned, rejected = clean_data(raw)
            logger.info(f"attempt={attempt}, stage=clean, status=completed")
            return cleaned, rejected, attempt - 1  # retry_count
        except Exception as e:
            logger.error(f"attempt={attempt}, stage=extract+clean, status=failed, error={e}")
            if attempt == max_retries + 1:
                raise
    return [], [], max_retries + 1


def generate_report(cleaned: List[Dict], rejected: List[Dict], retry_count: int, source_files: List[str]):
    processed_count = len(cleaned)
    rejected_count = len(rejected)
    report = {
        'processed_count': processed_count,
        'rejected_count': rejected_count,
        'retry_count': retry_count,
        'source_files': source_files
    }
    logger.info("report generated")
    print(json.dumps(report, indent=2))
    print("See memory/memory_summary.md for historical decisions.")
    return report
