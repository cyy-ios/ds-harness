import os
import json
import csv
import logging
from datetime import datetime, timezone
from mini_harness.utils import snake_case

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self, input_files, output_dir):
        self.input_files = input_files
        self.output_dir = output_dir
        self.extract_data = []
        self.clean_data = []
        self.rejects = []
        self.retry_count = 0
        self.processed_count = 0
        self.rejected_count = 0
        self.logs = []
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

    def extract(self):
        self.log(1, "extract", "start")
        all_records = []
        for f in self.input_files:
            if not os.path.exists(f):
                self.log(1, "extract", "error", f"File not found: {f}")
                continue
            ext = os.path.splitext(f)[1].lower()
            try:
                if ext == '.csv':
                    with open(f, newline='', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            # Skip empty rows (all fields empty or row entirely empty)
                            if any(v.strip() for v in row.values() if v):
                                all_records.append(row)
                elif ext == '.jsonl':
                    with open(f, encoding='utf-8') as jf:
                        for line in jf:
                            line = line.strip()
                            if line:
                                all_records.append(json.loads(line))
                else:
                    self.log(1, "extract", "error", f"Unsupported file type: {ext}")
                    continue
            except Exception as e:
                self.log(1, "extract", "error", str(e))
        self.extract_data = all_records
        self.log(1, "extract", "success", f"Extracted {len(all_records)} records")

    def clean(self):
        self.log(1, "clean", "start")
        cleaned = []
        rejects = []
        for record in self.extract_data:
            # Convert keys to snake_case
            new_record = {snake_case(k): v for k, v in record.items()}
            # Remove empty lines (already handled in extract)
            # Check for missing id
            if 'id' not in new_record or not str(new_record['id']).strip():
                rejects.append(new_record)
                continue
            cleaned.append(new_record)
        self.clean_data = cleaned
        self.rejects = rejects
        self.processed_count = len(cleaned)
        self.rejected_count = len(rejects)
        self.log(1, "clean", "success", f"Cleaned: {len(cleaned)} records, Rejected: {len(rejects)}")

    def report(self):
        self.log(1, "report", "start")
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
        self.log(1, "report", "success", f"Report written to {report_path}")
        # Write memory_summary.md
        memory_dir = os.path.join(self.output_dir, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        summary = f"# Memory Summary\n\n- Processed count: {self.processed_count}\n- Rejected count: {self.rejected_count}\n- Retry count: {self.retry_count}\n- Source files: {self.input_files}\n"
        with open(os.path.join(memory_dir, "memory_summary.md"), 'w', encoding='utf-8') as f:
            f.write(summary)
        self.log(1, "memory", "written", "memory_summary.md created")

    def run(self):
        attempts = 3
        for attempt in range(1, attempts+1):
            try:
                self.extract()
                self.clean()
                self.report()
                break
            except Exception as e:
                self.log(attempt, "pipeline", "error", str(e))
                if attempt == attempts:
                    self.retry_count = attempts - 1
                    self.log(attempt, "pipeline", "failed", "Max retries exceeded")
                else:
                    self.retry_count = attempt
                    self.log(attempt, "pipeline", "retry", f"Retrying after error: {e}")
        # Ensure memory_summary.md is written even if no report (but it's already written in report method)
        # If report is called inside, memory_summary is written. If error occurs before, it won't be written but that's fine.
