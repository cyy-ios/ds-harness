import logging
from pathlib import Path
from mini_harness.run import extract, clean, build_report

logger = logging.getLogger(__name__)

def run_dag(input_paths):
    """Process multiple input files, return aggregated report."""
    total_cleaned = 0
    total_rejected = 0
    total_retry = 0
    source_files = []
    for path in input_paths:
        logger.info(f'attempt=1, stage=extract, status=start')
        try:
            records = extract(path)
        except Exception as e:
            logger.error(f'attempt=1, stage=extract, status=failed, error={e}')
            total_retry += 2
            continue

        logger.info(f'attempt=1, stage=clean, status=start')
        try:
            cleaned, rejects = clean(records)
        except Exception as e:
            logger.error(f'attempt=1, stage=clean, status=failed, error={e}')
            total_retry += 2
            continue

        total_cleaned += len(cleaned)
        total_rejected += len(rejects)
        source_files.append(str(Path(path).resolve()))

    report = build_report(total_cleaned, total_rejected, total_retry, source_files)
    logger.info(f'attempt=1, stage=report, status=completed')
    return report
