import os
import tempfile
import subprocess
import shutil

def test_harness_from_workbench():
    # Create a temporary workbench
    with tempfile.TemporaryDirectory() as workbench:
        # Create input data in workbench
        csv_path = os.path.join(workbench, "input.csv")
        with open(csv_path, 'w') as f:
            f.write("id,name\n1,Alice\n2,Bob\n")
        jsonl_path = os.path.join(workbench, "events.jsonl")
        with open(jsonl_path, 'w') as f:
            pass
        output_dir = os.path.join(workbench, "output")
        
        # Determine harness.py location (repo root)
        harness_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'harness.py'))
        # Run from workbench using harness.py (which sets sys.path to include src)
        result = subprocess.run(
            ["python", harness_script, "run", csv_path, jsonl_path, "--output-dir", output_dir],
            capture_output=True,
            text=True,
            cwd=workbench
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Check that report.json was created
        report_path = os.path.join(output_dir, "report.json")
        assert os.path.exists(report_path)
        import json
        with open(report_path) as f:
            report = json.load(f)
        assert report["processed_count"] == 2
        assert report["rejected_count"] == 0
