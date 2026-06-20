import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List

logger = logging.getLogger(__name__)

_RETRY_CONFIG = {"max_attempts": 3}  # default total attempts (1 initial + 2 retries)

class RetryExceededError(Exception):
    pass

def retry_stage(stage_name: str, max_attempts: int = None):
    """Decorator to retry a stage function when an exception occurs. 
    Records attempt, stage, status in logs. First attempt is 0."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = max_attempts if max_attempts is not None else _RETRY_CONFIG.get("max_attempts", 3)
            for attempt in range(attempts):
                try:
                    logger.info(json.dumps({"attempt": attempt, "stage": stage_name, "status": "started"}))
                    result = func(*args, **kwargs)
                    logger.info(json.dumps({"attempt": attempt, "stage": stage_name, "status": "completed"}))
                    wrapper.retries_used = attempt  # retry count = attempt number
                    wrapper.success = True
                    return result
                except Exception as e:
                    logger.error(json.dumps({"attempt": attempt, "stage": stage_name, "status": "failed", "error": str(e)}))
                    if attempt == attempts - 1:
                        wrapper.retries_used = attempts - 1  # max retries
                        wrapper.success = False
                        raise RetryExceededError(f"Stage {stage_name} failed after {attempts} attempts") from e
            return None
        return wrapper
    return decorator

def snake_case(s: str) -> str:
    """Convert string to snake_case: lower, replace spaces/special with underscore."""
    return '_'.join(s.strip().lower().split())

def extract(file_path: str) -> Iterator[Dict[str, Any]]:
    """Extract records from CSV or JSONL file, skip empty lines."""
    ext = Path(file_path).suffix.lower()
    if ext == '.csv':
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # remove empty lines: if no keys or all values empty? Actually CSV will have keys even if empty. Skip if all field values are empty strings.
                if all(v == '' for v in row.values()):
                    continue
                yield row
    elif ext == '.jsonl':
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

@retry_stage("extract")
def extract_all(files: List[str]) -> List[Dict[str, Any]]:
    all_records = []
    for file_path in files:
        for record in extract(file_path):
            record['_source_file'] = file_path
            all_records.append(record)
    return all_records

@retry_stage("clean")
def clean(records: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Clean records: snake_case fields, reject records without 'id'."""
    cleaned = []
    rejects = []
    for record in records:
        # Convert field names to snake_case
        new_record = {}
        for key, value in record.items():
            new_key = snake_case(key)
            new_record[new_key] = value
        # Check for missing 'id' (case sensitive after conversion? It should be 'id' as per snake_case of 'ID' or 'id').
        if 'id' not in new_record or not new_record['id']:
            rejects.append(new_record)
        else:
            cleaned.append(new_record)
    return cleaned, rejects

@retry_stage("report")
def generate_report(cleaned: List[Dict[str, Any]], rejects: List[Dict[str, Any]], retry_count: int, source_files: List[str]) -> Dict[str, Any]:
    report = {
        "processed_count": len(cleaned),
        "rejected_count": len(rejects),
        "retry_count": retry_count,
        "source_files": source_files
    }
    # Refer to memory summary
    with open("memory/memory_summary.md", 'r', encoding='utf-8') as f:
        memory_content = f.read()
    report["memory_reference"] = memory_content[:200]  # truncate for brevity
    return report

def run(files: List[str], config: dict = None):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    # Apply config to retry attempts
    if config:
        retry_max = config.get("retry_attempts")
        if retry_max is not None:
            _RETRY_CONFIG["max_attempts"] = retry_max + 1  # attempts = initial + retries
    retry_count = 0
    try:
        extracted = extract_all(files)
        retry_count += extract_all.retries_used if hasattr(extract_all, 'retries_used') else 0
    except RetryExceededError:
        retry_count += extract_all.retries_used if hasattr(extract_all, 'retries_used') else 0
        extracted = []
    
    try:
        cleaned, rejects = clean(extracted)
        retry_count += clean.retries_used if hasattr(clean, 'retries_used') else 0
    except RetryExceededError:
        retry_count += clean.retries_used if hasattr(clean, 'retries_used') else 0
        cleaned, rejects = [], []
    
    try:
        report = generate_report(cleaned, rejects, retry_count, files)
    except RetryExceededError:
        retry_count += generate_report.retries_used if hasattr(generate_report, 'retries_used') else 0
        report = {"processed_count": 0, "rejected_count": 0, "retry_count": retry_count, "source_files": files}
    
    logger.info("Final Report:")
    logger.info(json.dumps(report, indent=2))
