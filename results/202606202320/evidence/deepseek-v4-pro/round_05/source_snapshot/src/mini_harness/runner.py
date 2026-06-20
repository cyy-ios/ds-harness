import logging
from mini_harness.pipeline import extract, clean, snake_case
from pathlib import Path

logger = logging.getLogger(__name__)

def run_dag(input_files):
    """
    Minimal DAG runner: extract -> clean -> return stats.
    Does not generate report file; returns dict with counts.
    """
    all_processed = []
    all_rejects = []
    for file_path in input_files:
        logger.info("Processing %s", file_path)
        records = extract(file_path)
        processed, rejects = clean(records)
        all_processed.extend(processed)
        all_rejects.extend(rejects)
    return {
        "processed_count": len(all_processed),
        "rejected_count": len(all_rejects),
        "source_files": input_files
    }
