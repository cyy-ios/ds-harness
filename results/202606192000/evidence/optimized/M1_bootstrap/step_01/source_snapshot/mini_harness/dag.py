"""DAG 流水线：extract → clean → report。"""
from pathlib import Path
from typing import Any, Dict, List

from mini_harness.extract import extract
from mini_harness.clean import clean
from mini_harness.report import generate_report
from mini_harness.logger import log


def run_pipeline(source_files: List[Path], repo_root: Path) -> Dict[str, Any]:
    """执行完整 DAG。"""
    all_cleaned: List[dict[str, Any]] = []
    all_rejects: List[dict[str, Any]] = []
    total_retries = 0
    source_strs: List[str] = []

    for source in source_files:
        source_strs.append(str(source))
        log(1, "dag", "start", source=str(source))

        records = extract(source)
        cleaned, rejects = clean(records)

        all_cleaned.extend(cleaned)
        all_rejects.extend(rejects)

    report = generate_report(
        cleaned=all_cleaned,
        rejects=all_rejects,
        source_files=source_strs,
        retry_count=total_retries,
        repo_root=repo_root,
    )
    log(1, "dag", "done", **report)
    return report
