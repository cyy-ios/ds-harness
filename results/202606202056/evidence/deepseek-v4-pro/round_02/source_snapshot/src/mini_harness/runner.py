import csv
import io
import json
import logging
import os
from typing import Dict, List, Any
from .utils import to_snake_case

logger = logging.getLogger(__name__)

def run_pipeline(file_paths: List[str]) -> Dict[str, Any]:
    """Run extract, clean, report stages."""
    source_files = [os.path.basename(p) for p in file_paths]
    retry_count = 0
    processed_count = 0
    rejected_count = 0
    all_records = []

    for fp in file_paths:
        records = extract(fp)
        clean_records, rejects = clean(records)
        processed_count += len(clean_records)
        rejected_count += len(rejects)
        all_records.extend(clean_records)

    report = {
        'processed_count': processed_count,
        'rejected_count': rejected_count,
        'retry_count': retry_count,
        'source_files': source_files
    }
    return report

def extract(file_path: str) -> List[dict]:
    """Extract records from CSV or JSONL file."""
    logger.info("extract attempt 1 stage=extract status=start file=%s", file_path)
    _, ext = os.path.splitext(file_path)
    records = []
    if ext == '.csv':
        try:
            with open(file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # remove empty rows
                    if all(v == '' for v in row.values()):
                        continue
                    # Convert keys to snake_case
                    new_row = {to_snake_case(k): v for k, v in row.items()}
                    records.append(new_row)
        except Exception:
            logger.exception("extract failed for %s", file_path)
            return []
    elif ext == '.jsonl':
        try:
            with open(file_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    # Convert keys to snake_case
                    new_obj = {to_snake_case(k): v for k, v in obj.items()}
                    records.append(new_obj)
        except Exception:
            logger.exception("extract failed for %s", file_path)
            return []
    else:
        logger.warning("Unsupported file type: %s", file_path)
    logger.info("extract attempt 1 stage=extract status=success file=%s records=%d", file_path, len(records))
    return records

def clean(records: List[dict]) -> (List[dict], List[dict]):
    """Clean records: reject those missing 'id' field (after snake_case conversion)."""
    logger.info("clean attempt 1 stage=clean status=start")
    clean_records = []
    rejects = []
    for rec in records:
        if rec.get('id') == '' or 'id' not in rec:
            rejects.append(rec)
            logger.info("clean attempt 1 stage=clean status=reject record=%s", rec)
        else:
            clean_records.append(rec)
    logger.info("clean attempt 1 stage=clean status=success clean=%d rejects=%d", len(clean_records), len(rejects))
    return clean_records, rejects
