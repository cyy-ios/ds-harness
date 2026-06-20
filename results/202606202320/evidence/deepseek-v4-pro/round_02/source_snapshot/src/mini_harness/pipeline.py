import csv
import json
import logging
import os
import re
from pathlib import Path
from mini_harness.config import Config

logger = logging.getLogger(__name__)


def extract(file_path):
    """Extract records from CSV or JSONL file."""
    path = Path(file_path)
    if path.suffix == '.csv':
        return extract_csv(path)
    elif path.suffix == '.jsonl':
        return extract_jsonl(path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


def extract_csv(path):
    records = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def extract_jsonl(path):
    records = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def snake_case(text):
    """Convert field name to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def clean(records):
    """
    Clean records:
    - Remove empty rows
    - Convert field names to snake_case
    - Reject records missing 'id'
    """
    processed = []
    rejects = []
    for record in records:
        if not any(v for v in record.values() if v.strip()):
            continue  # empty row
        cleaned = {snake_case(k): v for k, v in record.items()}
        if 'id' not in cleaned:
            rejects.append(cleaned)
        else:
            processed.append(cleaned)
    return processed, rejects


def report(processed, rejects, retry_count, source_files, output_file):
    """Generate JSON report."""
    report_data = {
        "processed_count": len(processed),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files,
        "memory_reference": "memory/memory_summary.md"
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    logger.info("Report saved to %s", output_file)


def run_pipeline(input_files, config=None):
    """Run the data processing pipeline using given Config."""
    if config is None:
        config = Config()
    max_retries = config.get("max_retries", 2)
    all_processed = []
    all_rejects = []
    total_retries = 0

    for file_path in input_files:
        attempt = 0
        while attempt <= max_retries:
            stage = "extract"
            try:
                logger.info("Stage: %s, Attempt: %d, File: %s, Status: start", stage, attempt, file_path)
                records = extract(file_path)
                logger.info("Stage: %s, Attempt: %d, File: %s, Status: success", stage, attempt, file_path)
                break
            except Exception as e:
                logger.error("Stage: %s, Attempt: %d, File: %s, Status: fail, Error: %s", stage, attempt, file_path, str(e))
                attempt += 1
                total_retries += 1
                if attempt > max_retries:
                    raise RuntimeError(f"Failed to extract {file_path} after {max_retries} retries: {e}")
        stage = "clean"
        logger.info("Stage: %s, Attempt: %d, File: %s, Status: start", stage, attempt, file_path)
        processed, rejects = clean(records)
        logger.info("Stage: %s, Attempt: %d, File: %s, Status: success, Processed: %d, Rejected: %d", stage, attempt, file_path, len(processed), len(rejects))
        all_processed.extend(processed)
        all_rejects.extend(rejects)

    stage = "report"
    logger.info("Stage: %s, Status: start", stage)
    report(all_processed, all_rejects, total_retries, input_files, config.get("output", "report.json"))
    logger.info("Stage: %s, Status: success", stage)
