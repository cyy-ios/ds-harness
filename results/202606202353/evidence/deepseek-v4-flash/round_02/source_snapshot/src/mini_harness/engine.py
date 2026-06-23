import csv
import json
import os
import sys

def run_pipeline(input_path, output_path):
    stage = "extract"
    attempt = 0
    max_retries = 2
    log_entry = {"stage": stage, "attempt": attempt, "status": "started"}
    print(json.dumps(log_entry))
    
    records = []
    # extract
    for attempt in range(1, max_retries + 2):
        try:
            records = extract(input_path)
            log_entry = {"stage": "extract", "attempt": attempt, "status": "success"}
            print(json.dumps(log_entry))
            break
        except Exception as e:
            log_entry = {"stage": "extract", "attempt": attempt, "status": "failed", "error": str(e)}
            print(json.dumps(log_entry))
            if attempt > max_retries:
                log_entry = {"stage": "extract", "attempt": attempt, "status": "abort"}
                print(json.dumps(log_entry))
                sys.exit(1)
    
    # clean
    for attempt in range(1, max_retries + 2):
        try:
            cleaned, rejected = clean(records)
            log_entry = {"stage": "clean", "attempt": attempt, "status": "success"}
            print(json.dumps(log_entry))
            break
        except Exception as e:
            log_entry = {"stage": "clean", "attempt": attempt, "status": "failed", "error": str(e)}
            print(json.dumps(log_entry))
            if attempt > max_retries:
                log_entry = {"stage": "clean", "attempt": attempt, "status": "abort"}
                print(json.dumps(log_entry))
                sys.exit(1)
    
    # report
    for attempt in range(1, max_retries + 2):
        try:
            report = generate_report(cleaned, rejected, input_path)
            log_entry = {"stage": "report", "attempt": attempt, "status": "success"}
            print(json.dumps(log_entry))
            break
        except Exception as e:
            log_entry = {"stage": "report", "attempt": attempt, "status": "failed", "error": str(e)}
            print(json.dumps(log_entry))
            if attempt > max_retries:
                log_entry = {"stage": "report", "attempt": attempt, "status": "abort"}
                print(json.dumps(log_entry))
                sys.exit(1)
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # memory summary reference
    memory_path = "memory/memory_summary.md"
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory_summary = f.read()
        with open(output_path, "r") as f:
            report_data = json.load(f)
        report_data["memory_summary_reference"] = memory_path
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)

def extract(input_path):
    records = []
    if input_path.endswith(".csv"):
        with open(input_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # remove empty rows
                if any(row.values()):
                    records.append(row)
    elif input_path.endswith(".jsonl"):
        with open(input_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    else:
        raise ValueError(f"Unsupported file format: {input_path}")
    return records

def clean(records):
    cleaned = []
    rejected = []
    for rec in records:
        # convert field names to snake_case
        new_rec = {}
        for k, v in rec.items():
            snake_key = k.strip().lower().replace(" ", "_")
            new_rec[snake_key] = v
        # ensure 'id' field
        if "id" not in new_rec:
            rejected.append(new_rec)
        else:
            cleaned.append(new_rec)
    return cleaned, rejected

def generate_report(cleaned, rejected, input_path):
    retry_count = 0  # simplified; actual retry count could be tracked globally
    return {
        "processed_count": len(cleaned),
        "rejected_count": len(rejected),
        "retry_count": retry_count,
        "source_files": [input_path]
    }
