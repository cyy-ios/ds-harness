import csv
import json
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def to_snake_case(name):
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
    return re.sub(r'[^a-zA-Z0-9]', '_', s2).lower()


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
        if not rec or all(v is None or (isinstance(v, str) and v.strip() == '') for v in rec.values()):
            continue
        new_rec = {}
        for k, v in rec.items():
            new_key = to_snake_case(k)
            new_rec[new_key] = v
        if 'id' not in new_rec or new_rec['id'] is None or (isinstance(new_rec['id'], str) and new_rec['id'].strip() == ''):
            rejects.append(new_rec)
        else:
            cleaned.append(new_rec)
    return cleaned, rejects


def build_report(cleaned_count, rejected_count, retry_count, source_files):
    """Return report dict with required fields."""
    report = {
        'processed_count': cleaned_count,
        'rejected_count': rejected_count,
        'retry_count': retry_count,
        'source_files': source_files
    }
    # Include memory summary reference
    memory_path = Path('memory/memory_summary.md')
    if memory_path.exists():
        with open(memory_path, 'r', encoding='utf-8') as mf:
            report['memory_summary'] = mf.read()
    else:
        report['memory_summary'] = 'memory/memory_summary.md not found'
    return report


def run_pipeline(input_path, output_path):
    """Execute DAG: extract -> clean -> report, with up to 2 retries."""
    max_retries = 2
    result = None

    for attempt in range(1, max_retries + 1):
        retry_count = attempt - 1  # number of previous failed attempts
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
            report = build_report(len(cleaned), len(rejects), retry_count, [str(input_path)])
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            logger.info(f'attempt={attempt}, stage=report, status=completed')
            result = report
            break
        except Exception as e:
            logger.error(f'attempt={attempt}, stage=report, status=failed, error={e}')
            if attempt == max_retries:
                raise
            continue

    if result is None:
        raise RuntimeError('Pipeline failed after max retries')
    return result
