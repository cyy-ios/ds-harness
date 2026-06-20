import logging
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from mini_harness.harness import DagRunner, extract, clean_data

def test_dag_runner_success():
    runner = DagRunner(max_retries=2)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("ID,User Name,Score\n1,Alice,10\n2,Bob,20\n")
    try:
        report = runner.run([f.name])
        assert report['final_stats']['processed_count'] == 2
        assert report['final_stats']['rejected_count'] == 0
        assert report['final_stats']['retry_count'] == 0
        assert len(report['final_stats']['source_files']) == 1
    finally:
        Path(f.name).unlink()

def test_dag_runner_extract_retry():
    """Test retry on extract failure."""
    runner = DagRunner(max_retries=2)
    # Patch extract to fail twice then succeed
    original_extract = extract
    call_count = [0]
    def mock_extract(filepath):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise ValueError("simulated extract failure")
        return original_extract(filepath)
    with patch('mini_harness.harness.extract', mock_extract):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ID,User Name,Score\n1,Alice,10\n")
        try:
            report = runner.run([f.name])
            # extract success on 3rd attempt, clean passes, retry_count from extract = 2
            assert report['final_stats']['processed_count'] == 1
            assert report['final_stats']['rejected_count'] == 0
            assert report['final_stats']['retry_count'] == 2
        finally:
            Path(f.name).unlink()

def test_dag_runner_clean_retry():
    """Test retry on clean failure."""
    runner = DagRunner(max_retries=2)
    original_clean = clean_data
    call_count = [0]
    def mock_clean(data):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise RuntimeError("simulated clean failure")
        return original_clean(data)
    with patch('mini_harness.harness.clean_data', mock_clean):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ID,User Name,Score\n1,Alice,10\n")
        try:
            report = runner.run([f.name])
            # extract passes, clean fails twice then succeeds, retry_count from clean = 2
            assert report['final_stats']['processed_count'] == 1
            assert report['final_stats']['rejected_count'] == 0
            assert report['final_stats']['retry_count'] == 2
        finally:
            Path(f.name).unlink()

def test_dag_runner_total_failure():
    """Test that after max_retries+1 attempts, exception is propagated."""
    runner = DagRunner(max_retries=2)
    with patch('mini_harness.harness.extract', side_effect=ValueError("always fail")):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("ID,User Name,Score\n1,Alice,10\n")
        try:
            import pytest
            with pytest.raises(ValueError):
                runner.run([f.name])
        finally:
            Path(f.name).unlink()

def test_dag_runner_logging(caplog):
    """Check structured logging."""
    runner = DagRunner(max_retries=1)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("ID,User Name,Score\n1,Alice,10\n")
    try:
        caplog.set_level(logging.INFO, logger="mini_harness.harness")
        report = runner.run([f.name])
        # verify logs contain attempt, stage, status
        log_messages = [r.message for r in caplog.records]
        assert any("attempt=1, stage=extract, status=started" in msg for msg in log_messages)
        assert any("attempt=1, stage=extract, status=completed" in msg for msg in log_messages)
        assert any("attempt=1, stage=clean, status=started" in msg for msg in log_messages)
        assert any("attempt=1, stage=clean, status=completed" in msg for msg in log_messages)
    finally:
        Path(f.name).unlink()
