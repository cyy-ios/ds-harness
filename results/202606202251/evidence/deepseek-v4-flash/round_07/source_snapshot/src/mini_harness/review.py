import json
from pathlib import Path
from mini_harness.run import get_project_root, run_pipeline


def generate_review_report(output_path='review_report.json'):
    """Generate a memory-aware review report."""
    root = get_project_root()
    
    # Read memory summary
    memory_path = root / 'memory' / 'memory_summary.md'
    if memory_path.exists():
        with open(memory_path, 'r', encoding='utf-8') as f:
            memory_content = f.read()
    else:
        memory_content = 'memory/memory_summary.md not found'
    
    # Read compatibility notes
    compat_path = root / 'docs' / 'compatibility-notes.md'
    if compat_path.exists():
        with open(compat_path, 'r', encoding='utf-8') as f:
            compat_content = f.read()
    else:
        compat_content = 'docs/compatibility-notes.md not found'
    
    # Read perf baseline
    perf_path = root / 'benchmarks' / 'perf-baseline.json'
    if perf_path.exists():
        with open(perf_path, 'r', encoding='utf-8') as f:
            perf_content = json.load(f)
    else:
        perf_content = 'benchmarks/perf-baseline.json not found'
    
    # Run current pipeline on sample data to get stats
    input_csv = root / 'data' / 'input.csv'
    temp_output = root / 'tmp_review_run.json'
    if input_csv.exists():
        try:
            pipeline_result = run_pipeline(str(input_csv), str(temp_output))
            # Clean up temp file
            if temp_output.exists():
                temp_output.unlink()
        except Exception as e:
            pipeline_result = {"error": str(e)}
    else:
        pipeline_result = {"error": "data/input.csv not found"}
    
    # Build review report
    review = {
        "design_decisions": memory_content,
        "compatibility_notes": compat_content,
        "performance_baseline": perf_content,
        "current_pipeline_stats": pipeline_result,
        "review_timestamp": None  # could add datetime but avoid imports
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(review, f, indent=2, ensure_ascii=False)
    
    return review
