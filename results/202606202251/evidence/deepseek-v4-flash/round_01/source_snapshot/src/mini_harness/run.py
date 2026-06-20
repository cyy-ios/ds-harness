import csv
import json
import logging
import os
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s2) if re.search('([a-z0-9])([A-Z])', s1) else s1
    return re.sub('[^a-zA-Z0-9]', '_', name).lower()


def extract(input_path):
    """Read CSV or JSONL, return list of dicts."""
    records = []
    ext = Path(input_path).suffix.lower()
    if ext == '.csv':
        with open(input_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    elif ext == '.jsonl':
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    else:
        raise ValueError(f'Unsupported file format: {ext}')
    return records


def clean(records):
    """Remove empty rows, convert field names to snake_case, separate rejects."""
    cleaned = []
    rejects = []
    for rec in records:
        # Remove empty rows (all values empty or None)
        if not rec or all(v is None or (isinstance(v, str) and v.strip() == '') for v in rec.values()):
            continue
        # Convert keys to snake_case
        new_rec = {}
        for k, v in rec.items():
            new_key = to_snake_case(k)
            new_rec[new_key] = v
        # Check for 'id' field, if missing -> reject
        if 'id' not in new_rec or new_rec['id'] is None or (isinstance(new_rec['id'], str) and new_rec['id'].strip() == ''):
            rejects.append(new_rec)
        else:
            cleaned.append(new_rec)
    return cleaned, rejects


def report_summary(cleaned_count, rejected_count, retry_count, source_files):
    """Return a summary dict."""
    summary = {
        'processed_count': cleaned_count,
        'rejected_count': rejected_count,
        'retry_count': retry_count,
        'source_files': source_files
    }
    return summary


def run_pipeline(input_path, output_path):
    """Execute the DAG: extract -> clean -> report, with retry."""
    max_retries = 2
    attempt = 1
    success = False
    retry_count = 0
    for attempt in range(1, max_retries + 1):
        logger.info(f'attempt={attempt}, stage=extract, status=start')
        try:
            records = extract(input_path)
        except Exception as e:
            logger.error(f'attempt={attempt}, stage=extract, status=failed, error={e}')
            if attempt == max_retries:
                raise
            continue

        logger.info(f'attempt={attempt}, stage=clean, status=start')
        try:
            cleaned, rejects = clean(records)
        except Exception as e:
            logger.error(f'attempt={attempt}, stage=clean, status=failed, error={e}')
            if attempt == max_retries:
                raise
            continue

        logger.info(f'attempt={attempt}, stage=report, status=start')
        try:
            summary = report_summary(len(cleaned), len(rejects), retry_count, [input_path])
            # Include memory summary reference
            memory_path = Path('memory/memory_summary.md')
            if memory_path.exists():
                with open(memory_path, 'r', encoding='utf-8') as mf:
                    summary['memory_summary'] = mf.read()
            else:
                summary['memory_summary'] = 'memory/memory_summary.md not found'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            success = True
            logger.info(f'attempt={attempt}, stage=report, status=completed')
            break
        except Exception as e:
            logger.error(f'attempt={attempt}, stage=report, status=failed, error={e}')
            retry_count += 1
            if attempt == max_retries:
                raise
            continue
    if not success:
        raise RuntimeError('Pipeline failed after max retries')
