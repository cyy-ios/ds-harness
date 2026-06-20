import csv
import json
import logging
import os
from typing import Any, Dict, List, Tuple
from .utils import to_snake_case

logger = logging.getLogger(__name__)


def _retry_stage(
    stage_name: str,
    max_retries: int,
    func,
    *args,
    **kwargs,
) -> Tuple[Any, int]:
    """
    Execute a stage function with retries up to max_retries.
    Returns (result, total_retries_used). Raises if all attempts exhausted.
    """
    for attempt in range(1, max_retries + 2):
        logger.info("%s attempt %d stage=%s status=start", stage_name, attempt, stage_name)
        try:
            result = func(*args, **kwargs)
            logger.info("%s attempt %d stage=%s status=success", stage_name, attempt, stage_name)
            return result, attempt - 1  # retry count is attempts-1
        except Exception as exc:
            logger.error("%s attempt %d stage=%s status=failure error=%s", stage_name, attempt, stage_name, exc)
            if attempt == max_retries + 1:
                raise
    # should not reach here
    raise RuntimeError(f"Unreachable code in {stage_name} retry")


def _extract_file(file_path: str) -> List[dict]:
    """Extract records from a CSV or JSONL file, raising on read errors."""
    _, ext = os.path.splitext(file_path)
    records = []
    if ext == '.csv':
        with open(file_path, encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        if not lines:
            return records
        import io
        csv_content = io.StringIO('\n'.join(lines))
        reader = csv.DictReader(csv_content)
        for row in reader:
            # skip completely empty rows
            if all(v == '' for v in row.values()):
                continue
            new_row = {to_snake_case(k): v for k, v in row.items()}
            records.append(new_row)
    elif ext == '.jsonl':
        with open(file_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                new_obj = {to_snake_case(k): v for k, v in obj.items()}
                records.append(new_obj)
    else:
        logger.warning("Unsupported file type, skipping: %s", file_path)
    return records


def _clean_records(records: List[dict]) -> Tuple[List[dict], List[dict]]:
    """
    Clean records: reject those missing a non-empty 'id' field.
    Returns (clean_records, rejects).
    """
    clean_records = []
    rejects = []
    for rec in records:
        if rec.get('id', '') == '':
            rejects.append(rec)
            logger.info("clean record rejected due to missing id: %s", rec)
        else:
            clean_records.append(rec)
    return clean_records, rejects


def run_pipeline(file_paths: List[str], max_retries: int = 2) -> Dict[str, Any]:
    """Run the extract → clean → report DAG with retries."""
    source_files = [os.path.basename(p) for p in file_paths]
    total_retries = 0
    all_records = []

    # Stage 1: Extract (per file with retries)
    for fp in file_paths:
        try:
            records, retries = _retry_stage(
                'extract', max_retries, _extract_file, fp
            )
        except Exception:
            logger.exception("Extract failed for %s after %d retries", fp, max_retries)
            continue  # skip this file
        total_retries += retries
        all_records.extend(records)

    # Stage 2: Clean (with retries)
    try:
        clean_result, retries = _retry_stage(
            'clean', max_retries, _clean_records, all_records
        )
        clean_records, rejects = clean_result
        total_retries += retries
    except Exception:
        logger.exception("Clean stage failed after %d retries", max_retries)
        clean_records, rejects = [], all_records  # treat all as rejects

    processed_count = len(clean_records)
    rejected_count = len(rejects)

    report = {
        'processed_count': processed_count,
        'rejected_count': rejected_count,
        'retry_count': total_retries,
        'source_files': source_files,
    }
    return report
