import tempfile
import os
from mini_harness.pipeline import Pipeline

def run_dag(input_files):
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = Pipeline(input_files, tmpdir)
        pipeline.run()
        # The report is written to tmpdir/report.json, read it
        report_path = os.path.join(tmpdir, "report.json")
        if os.path.exists(report_path):
            import json
            with open(report_path) as f:
                report = json.load(f)
            return report
        else:
            return {"processed_count": 0, "rejected_count": 0, "retry_count": 0}
