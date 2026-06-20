import csv
import json
import logging
import sys
from mini_harness.utils import to_snake_case

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(message)s')

def structured_log_stage(attempt, stage, status, extra=None):
    log_entry = {'attempt': attempt, 'stage': stage, 'status': status}
    if extra:
        log_entry.update(extra)
    logger.info(json.dumps(log_entry))

def extract(filepath, attempt):
    """Extract records from CSV or JSONL file."""
    records = []
    if filepath.endswith('.csv'):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
    elif filepath.endswith('.jsonl'):
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
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
        # remove empty rows: if all values are empty string or None, skip entirely (treated as empty row)
        if all(not v or v.isspace() if isinstance(v, str) else v is None for v in rec.values()):
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

def run(config):
    input_file = config['input']
    max_retries = config.get('retry_count', 2)
    total_retries = 0
    source_files = [input_file]

    # extract with retry
    records = None
    for attempt in range(max_retries + 1):
        try:
            records = extract(input_file, attempt + 1)
            break
        except Exception as e:
            structured_log_stage(attempt + 1, 'extract', 'error', {'error': str(e)})
            total_retries += 1
            if attempt == max_retries:
                raise

    # clean with retry (rarely fails but just in case)
    processed = None
    rejected = None
    for attempt in range(max_retries + 1):
        try:
            processed, rejected = clean(records, attempt + 1)
            break
        except Exception as e:
            structured_log_stage(attempt + 1, 'clean', 'error', {'error': str(e)})
            total_retries += 1
            if attempt == max_retries:
                raise

    # report stage no retry (just generate report)
    structured_log_stage(1, 'report', 'success')
    return report(processed, rejected, total_retries, source_files)
