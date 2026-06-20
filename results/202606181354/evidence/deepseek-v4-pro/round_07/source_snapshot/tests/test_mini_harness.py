import os
import json
import tempfile
import sys
from mini_harness.pipeline import Pipeline

def test_basic_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Prepare input data without id column -> all rejected
        csv_content = "Name,Age\nAlice,30\nBob,25\n,30\n"
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        pipeline = Pipeline([csv_path], tmpdir)
        pipeline.run()

        # Check report exists
        report_path = os.path.join(tmpdir, "report.json")
        assert os.path.exists(report_path)
        with open(report_path) as f:
            report = json.load(f)
        assert report["processed_count"] == 0
        assert report["rejected_count"] == 3  # three records without id, including row with empty name and age=30

def test_with_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_content = "id,Name,Age\n1,Alice,30\n2,Bob,25\n,Charlie,22\n"
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        pipeline = Pipeline([csv_path], tmpdir)
        pipeline.run()

        report_path = os.path.join(tmpdir, "report.json")
        with open(report_path) as f:
            report = json.load(f)
        assert report["processed_count"] == 2
        assert report["rejected_count"] == 1
        # Also check memory_summary.md
        memory_path = os.path.join(tmpdir, "memory", "memory_summary.md")
        assert os.path.exists(memory_path)

def test_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_content = '{"id": "1", "name": "Alice"}\n{"name": "Bob"}\n'
        jsonl_path = os.path.join(tmpdir, "test.jsonl")
        with open(jsonl_path, 'w') as f:
            f.write(jsonl_content)

        pipeline = Pipeline([jsonl_path], tmpdir)
        pipeline.run()

        report_path = os.path.join(tmpdir, "report.json")
        with open(report_path) as f:
            report = json.load(f)
        assert report["processed_count"] == 1
        assert report["rejected_count"] == 1

def test_cli():
    import subprocess
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_content = "id,name\n1,Alice\n2,Bob\n"
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Determine absolute path to src directory (works from any working dir)
        src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
        env = {**os.environ, 'PYTHONPATH': src_dir}
        result = subprocess.run(["python", "-m", "mini_harness", "run", csv_path, "--output-dir", tmpdir], capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert os.path.exists(os.path.join(tmpdir, "report.json"))
