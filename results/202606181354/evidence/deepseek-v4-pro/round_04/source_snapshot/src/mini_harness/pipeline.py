import os
import json
import csv
import logging
from datetime import datetime, timezone
from mini_harness.utils import snake_case

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, input_files, output_dir, config=None):
        self.input_files = input_files
        self.output_dir = output_dir
        self.config = config or {}
        self.logs = []
        self.retry_count = 0
        self.processed_count = 0
        self.rejected_count = 0
        os.makedirs(output_dir, exist_ok=True)

    def log(self, attempt, stage, status, message=""):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt": attempt,
            "stage": stage,
            "status": status,
            "message": message
        }
        self.logs.append(entry)
        logger.info(f"{entry}")

    def extract(self, attempt):
        self.log(attempt, "extract", "start")
        all_records = []
        for f in self.input_files:
            if not os.path.exists(f):
                self.log(attempt, "extract", "error", f"File not found: {f}")
                continue
            ext = os.path.splitext(f)[1].lower()
            try:
                if ext == '.csv':
                    with open(f, newline='', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            if any(v.strip() for v in row.values() if v):
                                all_records.append(row)
                elif ext == '.jsonl':
                    with open(f, encoding='utf-8') as jf:
                        for line in jf:
                            line = line.strip()
                            if line:
                                all_records.append(json.loads(line))
                else:
                    self.log(attempt, "extract", "error", f"Unsupported file type: {ext}")
                    continue
            except Exception as e:
                self.log(attempt, "extract", "error", str(e))
        self.log(attempt, "extract", "success", f"Extracted {len(all_records)} records")
        return all_records

    def clean(self, attempt, records):
        self.log(attempt, "clean", "start")
        cleaned = []
        rejects = []
        for record in records:
            new_record = {snake_case(k): v for k, v in record.items()}
            if 'id' not in new_record or not str(new_record['id']).strip():
                rejects.append(new_record)
                continue
            cleaned.append(new_record)
        self.log(attempt, "clean", "success", f"Cleaned: {len(cleaned)} records, Rejected: {len(rejects)}")
        return cleaned, rejects

    def report(self, attempt):
        self.log(attempt, "report", "start")
        report = {
            "processed_count": self.processed_count,
            "rejected_count": self.rejected_count,
            "retry_count": self.retry_count,
            "source_files": self.input_files,
            "logs": self.logs
        }
        report_path = os.path.join(self.output_dir, "report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        self.log(attempt, "report", "success", f"Report written to {report_path}")
        memory_dir = os.path.join(self.output_dir, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        summary = f"# Memory Summary\n\n- Processed count: {self.processed_count}\n- Rejected count: {self.rejected_count}\n- Retry count: {self.retry_count}\n- Source files: {self.input_files}\n"
        with open(os.path.join(memory_dir, "memory_summary.md"), 'w', encoding='utf-8') as f:
            f.write(summary)
        self.log(attempt, "memory", "written", "memory_summary.md created")

    def run(self):
        max_retries = 2  # up to 2 retries, total attempts = 1 + 2 = 3
        retries = 0
        for attempt in range(max_retries + 1):
            try:
                # Stage 1: Extract
                records = self.extract(attempt + 1)
                # Stage 2: Clean
                cleaned, rejects = self.clean(attempt + 1, records)
                # Stage 3: Report (but we need to set counts first)
                self.processed_count = len(cleaned)
                self.rejected_count = len(rejects)
                self.retry_count = retries
                self.report(attempt + 1)
                return
            except Exception as e:
                self.log(attempt + 1, "pipeline", "error", str(e))
                if retries < max_retries:
                    retries += 1
                    self.log(attempt + 1, "pipeline", "retry", f"Retry {retries} of {max_retries}")
                else:
                    self.retry_count = retries
                    self.log(attempt + 1, "pipeline", "failed", "Max retries exceeded")
