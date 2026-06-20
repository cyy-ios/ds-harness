import csv
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple, Callable, Optional

logger = logging.getLogger(__name__)


def snake_case(s: str) -> str:
    s = s.strip()
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s)
    return s.lower().strip('_')


def parse_file(filepath: str) -> List[Dict]:
    if filepath.endswith('.csv'):
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            lines = f.readlines()
        # filter out empty lines and comment lines
        meaningful_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        if not meaningful_lines:
            return []
        # first meaningful line is header
        header_line = meaningful_lines[0]
        reader = csv.DictReader(meaningful_lines[1:], fieldnames=None)
        # need to set fieldnames from header_line parsed by csv.reader
        reader.fieldnames = csv.reader([header_line]).__next__()
        rows = []
        for row in reader:
            # skip empty rows (all values are empty)
            # row values may be None or lists (restkey)
            # flatten any list values to string join?
            # For restkey, we may want to keep the extra data, but for now store as string if list
            new_row = {}
            for k, v in row.items():
                if isinstance(v, list):
                    # join list items with comma
                    new_row[k] = ', '.join(str(x) for x in v)
                else:
                    new_row[k] = v
            # after flattening, check empty
            if all(v is None or (isinstance(v, str) and v.strip() == '') for v in new_row.values()):
                continue
            rows.append(new_row)
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
                if not isinstance(obj, dict):
                    logger.error(f"skipping non-dict JSON line: {line[:50]}...")
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


class DagRunner:
    """Simple DAG runner for extract -> clean -> report pipeline with retries."""
    
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
    
    def _retry_stage(self, stage_name: str, action: Callable, *args, **kwargs):
        retries = 0
        for attempt in range(1, self.max_retries + 2):
            try:
                logger.info(f"attempt={attempt}, stage={stage_name}, status=started")
                result = action(*args, **kwargs)
                logger.info(f"attempt={attempt}, stage={stage_name}, status=completed")
                return result, retries
            except Exception as e:
                retries += 1
                logger.error(f"attempt={attempt}, stage={stage_name}, status=failed, error={e}")
                if attempt == self.max_retries + 1:
                    raise
        # unreachable
        return None, retries
    
    def _process_file(self, filepath: str) -> Tuple[List[Dict], List[Dict], int]:
        raw, retries_ext = self._retry_stage('extract', extract, filepath)
        result, retries_clean = self._retry_stage('clean', clean_data, raw)
        # clean_data returns a tuple (cleaned, rejected)
        cleaned, rejected = result
        total_retries = retries_ext + retries_clean
        return cleaned, rejected, total_retries
    
    def run(self, input_files: List[str]) -> dict:
        cleaned_total = []
        rejected_total = []
        retry_total = 0
        source_files = [str(Path(p).resolve()) for p in input_files]
        for fp in input_files:
            cleaned, rejected, retries = self._process_file(fp)
            cleaned_total.extend(cleaned)
            rejected_total.extend(rejected)
            retry_total += retries
        processed_count = len(cleaned_total)
        rejected_count = len(rejected_total)
        from mini_harness.review import generate_review_report
        review_report = generate_review_report(processed_count, rejected_count, retry_total, source_files)
        logger.info("review report generated")
        print(json.dumps(review_report, indent=2))
        print("See memory/memory_summary.md for historical decisions.")
        return review_report
