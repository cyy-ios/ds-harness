import csv
import json
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

_PROJECT_ROOT = None

def get_project_root():
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        # Traverse upward from cwd looking for src/mini_harness
        path = Path.cwd().resolve()
        for parent in [path] + list(path.parents):
            if (parent / 'src' / 'mini_harness').is_dir():
                _PROJECT_ROOT = parent
                break
        if _PROJECT_ROOT is None:
            # Fallback: traverse from this file's location
            path = Path(__file__).resolve().parent
            for parent in [path] + list(path.parents):
                if (parent / 'src' / 'mini_harness').is_dir():
                    _PROJECT_ROOT = parent
                    break
        if _PROJECT_ROOT is None:
            _PROJECT_ROOT = Path.cwd()
    return _PROJECT_ROOT


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
            lines = [line for line in f if not line.startswith('#')]
            reader = csv.DictReader(lines)
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
    memory_path = get_project_root() / 'memory' / 'memory_summary.md'
    if memory_path.exists():
        with open(memory_path, 'r', encoding='utf-8') as mf:
            report['memory_summary'] = mf.read()
    else:
        report['memory_summary'] = 'memory/memory_summary.md not found'
    return report


def resolve_path(path_str):
    """Resolve path: if not absolute and doesn't exist, try relative to project root."""
    p = Path(path_str)
    if p.is_absolute():
        return str(p.resolve())
    # First try as relative to cwd
    if p.exists():
        return str(p.resolve())
    # Then try relative to project root
    candidate = get_project_root() / p
    if candidate.exists():
        return str(candidate.resolve())
    # Fallback: return resolved cwd relative (will likely fail later)
    return str(p.resolve())


def run_pipeline(input_path, output_path):
    """Execute DAG: extract -> clean -> report, with up to 2 retries."""
    resolved_input = resolve_path(input_path)
    max_retries = 2
    result = None

    for attempt in range(1, max_retries + 1):
        retry_count = attempt - 1
        logger.info(f'attempt={attempt}, stage=extract, status=start')
        try:
            records = extract(resolved_input)
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
            report = build_report(len(cleaned), len(rejects), retry_count, [resolved_input])
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
