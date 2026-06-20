import os
import tempfile
import json
from mini_harness.pipeline import DAGRunner

def test_dag_runner_basic():
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as tmp:
        tmp.write("Id,Name\n1,Alice\n,Bob\n2,Charlie\n")
        tmp_path = tmp.name
    try:
        runner = DAGRunner([tmp_path], output_dir='test_output', memory_path='nonexistent.md')
        stats, logs = runner.run()
        assert stats['processed_count'] == 2
        assert stats['rejected_count'] == 1  # Bob missing id
        assert stats['retry_count'] == 0
        assert len(logs) == 3  # one log per stage success
        assert logs[0]['stage'] == 'extract' and logs[0]['status'] == 'success'
        assert os.path.exists('test_output/report.json')
        with open('test_output/report.json') as f:
            report = json.load(f)
            assert report['processed_count'] == 2
            assert report['rejected_count'] == 1
    finally:
        os.unlink(tmp_path)
        # clean up test_output
        if os.path.exists('test_output'):
            import shutil
            shutil.rmtree('test_output')

def test_retry_logic():
    # Simulate a stage that fails twice then succeeds
    runner = DAGRunner([], output_dir='test_output')
    call_count = [0]
    def flaky():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise ValueError("fail")
        return "success"
    result = runner._retry(flaky, 'test_stage', max_retries=2)
    assert result == "success"
    assert call_count[0] == 3
    assert runner.stats['retry_count'] == 2
    # logs: one retry for attempt1, one retry for attempt2, success on attempt3
    assert len([l for l in runner.logs if l['stage'] == 'test_stage']) == 3
    assert runner.logs[-1]['status'] == 'success'
    assert runner.logs[0]['status'] == 'retry'
    assert runner.logs[1]['status'] == 'retry'
    # clean up
    if os.path.exists('test_output'):
        import shutil
        shutil.rmtree('test_output')
