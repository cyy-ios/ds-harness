import json
from pathlib import Path
from .runner import run, _REPO_ROOT

def retrospective_report(config: dict = None):
    """Generate a memory-aware retrospective report referencing early design decisions and current statistics."""
    # Read memory summary
    memory_path = _REPO_ROOT / "memory" / "memory_summary.md"
    if memory_path.exists():
        memory_content = memory_path.read_text(encoding='utf-8')
    else:
        memory_content = "No memory summary found."
    
    # Read compatibility notes
    compat_path = _REPO_ROOT / "docs" / "compatibility-notes.md"
    if compat_path.exists():
        compat_content = compat_path.read_text(encoding='utf-8')
    else:
        compat_content = "No compatibility notes."
    
    # Read performance baseline
    perf_path = _REPO_ROOT / "benchmarks" / "perf-baseline.json"
    if perf_path.exists():
        perf_data = json.loads(perf_path.read_text(encoding='utf-8'))
    else:
        perf_data = {}
    
    # Run a fresh data processing with all available test files to get current stats
    # Use default files from data directory if not provided via config
    test_files = [
        "data/input.csv",
        "data/events.jsonl",
        "data/m4_noise_test.csv"
    ]
    # Run the harness
    report = run(test_files, config=config)
    
    # Compile retrospective report
    lines = []
    lines.append("# Retrospective Report (Memory-Aware)")
    lines.append("")
    lines.append("## Early Design Decisions (from memory_summary.md)")
    # Extract key decisions
    decisions = []
    for line in memory_content.splitlines():
        if line.startswith("早期设计决策：") or line.startswith("历史偏好："):
            decisions.append(line.strip())
    if decisions:
        lines.extend(decisions)
    else:
        lines.append(memory_content.strip())
    lines.append("")
    lines.append("## Compatibility Notes Summarized")
    lines.append(compat_content.strip())
    lines.append("")
    lines.append("## Performance Baseline")
    lines.append(json.dumps(perf_data, ensure_ascii=False, indent=2))
    lines.append("")
    lines.append("## Current Processing Statistics")
    lines.append(f"- Processed count: {report.get('processed_count', 0)}")
    lines.append(f"- Rejected count: {report.get('rejected_count', 0)}")
    lines.append(f"- Retry count: {report.get('retry_count', 0)}")
    lines.append(f"- Source files: {report.get('source_files', [])}")
    if "memory_reference" in report:
        lines.append(f"- Memory reference excerpt: {report['memory_reference'][:100]}...")
    
    retrospective = "\n".join(lines)
    return retrospective
