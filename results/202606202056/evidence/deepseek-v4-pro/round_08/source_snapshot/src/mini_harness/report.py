"""Report generation for mini_harness."""
import json
import os
from typing import Any, Dict


def format_report(report: Dict[str, Any], format: str = 'text', memory_path: str = None) -> str:
    """
    Format a pipeline report according to the specified format.
    Supported formats: 'text', 'json', 'retro'.
    'retro' requires a memory_path to produce a retrospective report.
    """
    if format == 'json':
        return json.dumps(report, indent=2)
    elif format == 'retro':
        if not memory_path:
            memory_path = 'memory/memory_summary.md'
        return _generate_retrospective(report, memory_path)
    else:
        # plain text format
        lines = [
            f"processed_count: {report['processed_count']}",
            f"rejected_count: {report['rejected_count']}",
            f"retry_count: {report['retry_count']}",
            f"source_files: {report['source_files']}",
        ]
        return '\n'.join(lines)


def _generate_retrospective(report: Dict[str, Any], memory_path: str) -> str:
    """
    Generate a memory-aware retrospective report.
    Reads the memory summary and combines with current pipeline stats.
    """
    memory_content = ""
    if os.path.exists(memory_path):
        with open(memory_path, encoding='utf-8') as f:
            memory_content = f.read().strip()
    else:
        memory_content = "(memory summary not found)"

    lines = [
        "# Memory-Aware Retrospective Report",
        "",
        "## Current Run Statistics",
        f"- Processed: {report['processed_count']}",
        f"- Rejected: {report['rejected_count']}",
        f"- Retries: {report['retry_count']}",
        f"- Source files: {', '.join(report['source_files'])}",
        "",
        "## Memory Summary",
        "```",
        memory_content,
        "```",
        "",
        "## Discernment Note",
        "The retry_count above reflects the current execution. "
        "The memory summary may reference historical values which may differ from the present run.",
    ]
    return '\n'.join(lines)


def write_report_file(report: Dict[str, Any], file_path: str, format: str = 'text',
                      memory_path: str = None) -> None:
    """Write a formatted report to a file."""
    content = format_report(report, format=format, memory_path=memory_path)
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
