import os
import json
from datetime import datetime, timezone

class ReportGenerator:
    """Generates the pipeline execution report."""
    def __init__(self, output_dir, memory_path=None):
        self.output_dir = output_dir
        self.memory_path = memory_path

    def generate(self, stats, logs=None):
        os.makedirs(self.output_dir, exist_ok=True)
        report_path = os.path.join(self.output_dir, 'report.json')
        report = {
            'processed_count': stats.get('processed_count', 0),
            'rejected_count': stats.get('rejected_count', 0),
            'retry_count': stats.get('retry_count', 0),
            'source_files': stats.get('source_files', []),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        # include memory summary if exists
        if self.memory_path and os.path.exists(self.memory_path):
            with open(self.memory_path, encoding='utf-8') as f:
                memory = f.read().strip()
            report['memory_summary'] = memory
        else:
            report['memory_summary'] = None
        # optionally include logs
        if logs is not None:
            report['logs'] = logs
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        return report_path
