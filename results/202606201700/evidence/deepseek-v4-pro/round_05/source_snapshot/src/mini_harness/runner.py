import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

_RETRY_CONFIG = {"max_attempts": 3}  # default total attempts (1 initial + 2 retries)

def find_repo_root() -> Path:
    """Locate the repo root by looking for 'pyproject.toml' starting from the directory containing this file."""
    start = Path(__file__).resolve().parent
    for parent in start.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not locate repo root (pyproject.toml not found in parent directories)")

_REPO_ROOT = find_repo_root()

def resolve_input_path(file_path: str) -> Path:
    """Resolve a user-provided input path relative to the repo root if relative."""
    path = Path(file_path)
    if path.is_absolute():
        return path
    return _REPO_ROOT / path

def ensure_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def write_report(report: Dict[str, Any], path: Optional[str] = None):
    if path is None:
        path = _REPO_ROOT / "report.json"
    else:
        path = resolve_input_path(path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

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
    """Extract records from CSV or JSONL file, skip empty lines and comment lines (starting with '#').
    Handles CSV files with comments by reading all lines and ignoring those that start with '#'."""
    resolved = resolve_input_path(file_path)
    ext = resolved.suffix.lower()
    if ext == '.csv':
        with open(resolved, 'r', encoding='utf-8') as f:
            # Read all lines, filter out comments and empty lines
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        if not lines:
            return
        # First non-comment line is header
        header_line = lines[0]
        fieldnames = header_line.split(',')
        reader = csv.DictReader(lines[1:], fieldnames=fieldnames)
        for row in reader:
            # double-check empty rows
            if not row or all(v == '' for v in row.values()):
                continue
            yield row
    elif ext == '.jsonl':
        with open(resolved, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
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
        new_record = {}
        for key, value in record.items():
            new_key = snake_case(key)
            new_record[new_key] = value
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
    memory_path = _REPO_ROOT / "memory" / "memory_summary.md"
    if memory_path.exists():
        with open(memory_path, 'r', encoding='utf-8') as f:
            memory_content = f.read()
        report["memory_reference"] = memory_content[:200]
    return report

def run(files: List[str], config: dict = None) -> Dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
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
    
    # Write report to file if configured
    if config and "report_output" in config:
        write_report(report, config["report_output"])
    
    logger.info("Final Report:")
    logger.info(json.dumps(report, indent=2))
    return report

# Alias for backward compatibility with test_long_log_debug
run_dag = run
