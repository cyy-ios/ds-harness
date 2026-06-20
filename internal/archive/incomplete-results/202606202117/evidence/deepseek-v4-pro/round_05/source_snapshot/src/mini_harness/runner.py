import csv
import json
import logging
from mini_harness.utils import to_snake_case

logger = logging.getLogger(__name__)

def structured_log_stage(attempt, stage, status, extra=None):
    log_entry = {'attempt': attempt, 'stage': stage, 'status': status}
    if extra:
        log_entry.update(extra)
    logger.info(json.dumps(log_entry))

def extract(filepath, attempt):
    """Extract records from CSV or JSONL file, ignoring comment lines (#) and empty lines."""
    records = []
    if filepath.endswith('.csv'):
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [line for line in f if line.strip() and not line.lstrip().startswith('#')]
        if not lines:
            raise ValueError("No valid data in CSV")
        reader = csv.DictReader(lines)
        for row in reader:
            records.append(dict(row))
    elif filepath.endswith('.jsonl'):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    records.append(json.loads(line))
    else:
        raise ValueError(f"Unsupported file format: {filepath}")
    structured_log_stage(attempt, 'extract', 'success', {'records_extracted': len(records)})
    return records

def clean(records, attempt):
    """Clean records: remove empty records, convert keys to snake_case, reject records missing 'id'."""
    processed = []
    rejected = []
    for rec in records:
        # remove empty rows: if all values are empty string or None, skip entirely
        if all(not v or (isinstance(v, str) and v.isspace()) or v is None for v in rec.values()):
            continue
        # convert keys to snake_case
        new_rec = {}
        for key, value in rec.items():
            new_key = to_snake_case(key)
            new_rec[new_key] = value
        # check for 'id'
        if 'id' not in new_rec or not new_rec['id']:
            rejected.append(new_rec)
        else:
            processed.append(new_rec)
    structured_log_stage(attempt, 'clean', 'success', {'processed': len(processed), 'rejected': len(rejected)})
    return processed, rejected

def report(processed, rejected, retry_count, source_files):
    """Generate report dict."""
    return {
        'processed_count': len(processed),
        'rejected_count': len(rejected),
        'retry_count': retry_count,
        'source_files': source_files
    }

def _run_with_retry(func, *args, max_retries, stage):
    """Run a function with retry, returning (result, retries_used)."""
    retries = 0
    for attempt in range(max_retries + 1):
        try:
            result = func(*args, attempt + 1)
            return result, retries
        except Exception as e:
            structured_log_stage(attempt + 1, stage, 'error', {'error': str(e)})
            retries += 1
            if attempt == max_retries:
                raise

def run(config):
    """Run pipeline on a single input file."""
    input_file = config['input']
    max_retries = config.get('retry_count', 2)
    source_files = [input_file]

    records, retries1 = _run_with_retry(extract, input_file, max_retries=max_retries, stage='extract')
    (processed, rejected), retries2 = _run_with_retry(clean, records, max_retries=max_retries, stage='clean')
    total_retries = retries1 + retries2

    structured_log_stage(1, 'report', 'success')
    return report(processed, rejected, total_retries, source_files)

def run_dag(file_paths, max_retries=2):
    """Run pipeline on multiple input files, aggregating results."""
    all_processed = []
    all_rejected = []
    total_retries = 0

    for filepath in file_paths:
        records, retries1 = _run_with_retry(extract, filepath, max_retries=max_retries, stage='extract')
        (processed, rejected), retries2 = _run_with_retry(clean, records, max_retries=max_retries, stage='clean')
        total_retries += retries1 + retries2
        all_processed.extend(processed)
        all_rejected.extend(rejected)

    structured_log_stage(1, 'report', 'success')
    return report(all_processed, all_rejected, total_retries, file_paths)
