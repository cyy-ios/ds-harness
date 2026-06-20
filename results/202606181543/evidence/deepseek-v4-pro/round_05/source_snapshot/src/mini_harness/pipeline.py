import csv
import json
import logging
import os
import re
from datetime import datetime, timezone

def snake_case(s):
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    s = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()
    s = re.sub(r'[^a-z0-9_]+', '_', s).strip('_')
    return s

def parse_input(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row
    elif ext == '.jsonl':
        with open(file_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
    elif ext in ('.tsv', '.tab'):
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                yield row
    else:
        raise ValueError(f"Unsupported file type: {ext}")

class DAGRunner:
    """Simple DAG runner for extract -> clean -> report."""
    def __init__(self, input_files, output_dir='output', memory_path='memory/memory_summary.md'):
        self.input_files = input_files
        self.output_dir = output_dir
        self.memory_path = memory_path
        self.stats = {
            'processed_count': 0,
            'rejected_count': 0,
            'retry_count': 0,
            'source_files': input_files
        }
        self.logs = []
        self.records = []
        self.cleaned = []
        self.rejects = []

    def _retry(self, func, stage_name, max_retries=2):
        """Retry wrapper. max_retries is number of retries after first attempt. Total attempts = max_retries+1."""
        attempts = 0
        while attempts <= max_retries:
            try:
                result = func()
                log_entry = {
                    'stage': stage_name,
                    'attempt': attempts + 1,
                    'status': 'success',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                self.logs.append(log_entry)
                logging.info(f"{stage_name} succeeded on attempt {attempts+1}")
                return result
            except Exception as e:
                attempts += 1
                if attempts > max_retries:
                    log_entry = {
                        'stage': stage_name,
                        'attempt': attempts,
                        'status': 'failure',
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    self.logs.append(log_entry)
                    logging.error(f"{stage_name} failed after {attempts} attempts: {e}")
                    raise
                else:
                    logging.warning(f"{stage_name} attempt {attempts} failed: {e}")
                    log_entry = {
                        'stage': stage_name,
                        'attempt': attempts,
                        'status': 'retry',
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    self.logs.append(log_entry)
                    self.stats['retry_count'] += 1

    def extract(self):
        """Extract phase: collect records from input files."""
        def _extract():
            records = []
            for path in self.input_files:
                for rec in parse_input(path):
                    records.append(rec)
            return records
        self.records = self._retry(_extract, 'extract')
        logging.info(f"Extract completed: {len(self.records)} records extracted")

    def clean(self):
        """Clean phase: transform records, separate rejects."""
        def _clean():
            cleaned = []
            rejects = []
            for rec in self.records:
                # skip empty rows (all values empty)
                if all(v == '' for v in rec.values()):
                    continue
                # convert keys to snake_case
                new_rec = {}
                for k, v in rec.items():
                    new_key = snake_case(k)
                    new_rec[new_key] = v
                # check for missing 'id'
                if 'id' not in new_rec or not new_rec['id']:
                    rejects.append(new_rec)
                else:
                    cleaned.append(new_rec)
            return cleaned, rejects
        self.cleaned, self.rejects = self._retry(_clean, 'clean')
        self.stats['processed_count'] = len(self.cleaned)
        self.stats['rejected_count'] = len(self.rejects)
        logging.info(f"Clean completed: {len(self.cleaned)} cleaned, {len(self.rejects)} rejected")

    def report(self):
        """Generate report file with stats."""
        def _report():
            os.makedirs(self.output_dir, exist_ok=True)
            report_path = os.path.join(self.output_dir, 'report.json')
            report = {
                'processed_count': self.stats['processed_count'],
                'rejected_count': self.stats['rejected_count'],
                'retry_count': self.stats['retry_count'],
                'source_files': self.stats['source_files']
            }
            # include memory summary if exists
            if os.path.exists(self.memory_path):
                with open(self.memory_path, encoding='utf-8') as f:
                    memory = f.read()
                report['memory_summary'] = memory.strip()
            else:
                report['memory_summary'] = None
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            return report_path
        report_file = self._retry(_report, 'report')
        logging.info(f"Report generated: {report_file}")
        return report_file

    def run(self):
        self.extract()
        self.clean()
        self.report()
        return self.stats, self.logs

def run_pipeline(input_files, output_dir='output', memory_path='memory/memory_summary.md'):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    runner = DAGRunner(input_files, output_dir, memory_path)
    return runner.run()
