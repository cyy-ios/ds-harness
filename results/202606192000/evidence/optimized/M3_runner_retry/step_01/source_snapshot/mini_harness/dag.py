"""DAG pipeline: extract -> clean -> report with config-driven retry."""
from pathlib import Path
from typing import Any, Dict, List

from mini_harness.extract import extract
from mini_harness.clean import clean
from mini_harness.report import generate_report
from mini_harness.logger import log
from mini_harness.retry import reset_retry_counter, get_retry_counter


def run_pipeline(
    source_files: List[Path],
    repo_root: Path,
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Execute full DAG. Optional config dict drives retry settings."""
    if config is None:
        config = {}
    retry_cfg = config.get("retry", {})
    max_retries = retry_cfg.get("max_retries", 2)

    reset_retry_counter()

    all_cleaned: List[dict[str, Any]] = []
    all_rejects: List[dict[str, Any]] = []
    source_strs: List[str] = []

    for source in source_files:
        source_strs.append(str(source))
        log(1, "dag", "start", source=str(source))

        records = extract(source, max_retries=max_retries)
        cleaned, rejects = clean(records, max_retries=max_retries)

        all_cleaned.extend(cleaned)
        all_rejects.extend(rejects)

    total_retries = get_retry_counter()

    report = generate_report(
        cleaned=all_cleaned,
        rejects=all_rejects,
        source_files=source_strs,
        retry_count=total_retries,
        repo_root=repo_root,
        max_retries=max_retries,
    )
    log(1, "dag", "done", **report)
    return report