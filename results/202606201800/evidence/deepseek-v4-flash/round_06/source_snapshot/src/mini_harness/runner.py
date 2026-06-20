import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def _extract_file(file_path: str) -> List[dict]:
    """Extract records from a single file (CSV or JSONL)."""
    records = []
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with open(path, newline='') as f:
            # skip comment lines starting with '#'
            lines = [line for line in f if not line.startswith('#')]
            reader = csv.DictReader(lines)
            for row in reader:
                records.append(row)
    elif suffix == ".jsonl":
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
    return records

def _to_snake_case(name: str) -> str:
    """Convert field name to snake_case."""
    import re
    name = name.strip()
    name = re.sub(r'[^a-zA-Z0-9]+', '_', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    name = name.lower()
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def _clean_records(records: List[dict]) -> (List[dict], List[dict]):
    """Clean records: remove empty rows, convert field names to snake_case, reject missing id."""
    cleaned = []
    rejected = []
    for rec in records:
        # remove empty rows (all values empty or None)
        if all(v is None or (isinstance(v, str) and v.strip() == '') for v in rec.values()):
            continue
        # convert keys to snake_case
        new_rec = {}
        for k, v in rec.items():
            new_key = _to_snake_case(k)
            new_rec[new_key] = v
        # reject if id missing (empty or None)
        if 'id' not in new_rec or new_rec['id'] is None or (isinstance(new_rec['id'], str) and new_rec['id'].strip() == ''):
            rejected.append(new_rec)
        else:
            cleaned.append(new_rec)
    return cleaned, rejected

def _report(processed: int, rejected: int, retry_count: int, source_files: List[str]) -> dict:
    """Generate report dictionary."""
    return {
        "processed_count": processed,
        "rejected_count": rejected,
        "retry_count": retry_count,
        "source_files": source_files
    }

def run_dag(source_files: List[str], max_retries: int = 2) -> dict:
    """Run extract -> clean -> report with retry logic."""
    retry_count = 0
    total_processed = 0
    total_rejected = 0
    source_files_reported = []

    for attempt in range(1, max_retries + 2):  # original + retries
        if attempt > 1:
            retry_count += 1
            logger.info(f"attempt={attempt}, stage=retry, status=retrying")
        try:
            # Extract phase
            logger.info(f"attempt={attempt}, stage=extract, status=started")
            all_records = []
            for f in source_files:
                recs = _extract_file(f)
                all_records.extend(recs)
            logger.info(f"attempt={attempt}, stage=extract, status=completed, records={len(all_records)}")

            # Clean phase
            logger.info(f"attempt={attempt}, stage=clean, status=started")
            cleaned, rejected = _clean_records(all_records)
            logger.info(f"attempt={attempt}, stage=clean, status=completed, cleaned={len(cleaned)}, rejected={len(rejected)}")

            # Report phase
            logger.info(f"attempt={attempt}, stage=report, status=started")
            total_processed += len(cleaned)
            total_rejected += len(rejected)
            source_files_reported = source_files
            logger.info(f"attempt={attempt}, stage=report, status=completed")
            break
        except Exception as e:
            logger.error(f"attempt={attempt}, stage=error, status=failed, error={e}")
            if attempt > max_retries:
                raise

    return _report(total_processed, total_rejected, retry_count, source_files_reported)
