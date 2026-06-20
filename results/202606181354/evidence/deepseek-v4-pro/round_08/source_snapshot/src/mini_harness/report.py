import os
import json
import logging

logger = logging.getLogger(__name__)


def write_report(processed_count, rejected_count, retry_count, source_files, logs, output_dir):
    report = {
        "processed_count": processed_count,
        "rejected_count": rejected_count,
        "retry_count": retry_count,
        "source_files": source_files,
        "logs": logs
    }
    report_path = os.path.join(output_dir, "report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    logger.info(f"Report written to {report_path}")
    return report_path


def write_memory_summary(processed_count, rejected_count, retry_count, source_files, output_dir):
    memory_dir = os.path.join(output_dir, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    summary = f"# Memory Summary\n\n- Processed count: {processed_count}\n- Rejected count: {rejected_count}\n- Retry count: {retry_count}\n- Source files: {source_files}\n"
    memory_path = os.path.join(memory_dir, "memory_summary.md")
    with open(memory_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    logger.info("memory_summary.md created")
    return memory_path
