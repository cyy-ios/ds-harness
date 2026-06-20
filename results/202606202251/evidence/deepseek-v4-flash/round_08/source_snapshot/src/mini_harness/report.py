import json
from pathlib import Path

def build_report(cleaned_count, rejected_count, retry_count, source_files):
    """Return report dict with required fields, including memory summary."""
    report = {
        'processed_count': cleaned_count,
        'rejected_count': rejected_count,
        'retry_count': retry_count,
        'source_files': source_files
    }
    # Try to locate project root for memory/memory_summary.md
    # Simpler: assume cwd or traverse upward looking for memory folder
    memory_path = Path('memory') / 'memory_summary.md'
    if not memory_path.exists():
        # Traverse from cwd upward
        cwd = Path.cwd().resolve()
        for parent in [cwd] + list(cwd.parents):
            candidate = parent / 'memory' / 'memory_summary.md'
            if candidate.exists():
                memory_path = candidate
                break
    if memory_path.exists():
        with open(memory_path, 'r', encoding='utf-8') as mf:
            report['memory_summary'] = mf.read()
    else:
        report['memory_summary'] = 'memory/memory_summary.md not found'
    return report
