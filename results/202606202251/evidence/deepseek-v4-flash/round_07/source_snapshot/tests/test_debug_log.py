import json
import logging
from pathlib import Path
import pytest
from mini_harness.run import run_pipeline

def test_log_contains_required_attributes(caplog):
    caplog.set_level(logging.INFO)
    input_csv = Path('data/input.csv')
    output = Path('/tmp/test_report_m4.json')
    if output.exists():
        output.unlink()
    run_pipeline(str(input_csv), str(output))
    # Check log records contain attempt, stage, status
    for record in caplog.records:
        assert 'attempt=' in record.getMessage()
        assert 'stage=' in record.getMessage()
        assert 'status=' in record.getMessage()

def test_debug_output_on_retry(caplog):
    """Simulate a scenario that triggers retry: provide non-existent file."""
    caplog.set_level(logging.INFO)
    with pytest.raises(Exception):
        run_pipeline('nonexistent.csv', '/tmp/out.json')
    # Should have logged multiple attempts with failed status
    failed_messages = [r for r in caplog.records if 'failed' in r.getMessage()]
    assert len(failed_messages) >= 2  # at least 2 retries

def test_report_structure():
    output = Path('/tmp/test_report_m4.json')
    if output.exists():
        output.unlink()
    run_pipeline(str(Path('data/input.csv')), str(output))
    with open(output, 'r') as f:
        report = json.load(f)
    required_keys = ['processed_count', 'rejected_count', 'retry_count', 'source_files']
    for k in required_keys:
        assert k in report
    assert 'memory_summary' in report
