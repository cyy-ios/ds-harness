import csv
import json
import os
import sys

# Global retry counter
_retry_count = 0

def run_pipeline(input_path, output_path):
    global _retry_count
    _retry_count = 0

    # DAG stages
    stages = ["extract", "clean", "report"]
    state = {}

    # extract
    records = run_stage("extract", lambda: extract(input_path))
    state["records"] = records

    # clean
    cleaned, rejected = run_stage("clean", lambda: clean(state["records"]))
    state["cleaned"] = cleaned
    state["rejected"] = rejected

    # report
    report = run_stage("report", lambda: generate_report(state["cleaned"], state["rejected"], input_path))

    # write output
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

def run_stage(stage, func):
    global _retry_count
    max_retries = 2
    last_exception = None
    for attempt in range(1, max_retries + 2):
        log = {"stage": stage, "attempt": attempt, "status": "started"}
        print(json.dumps(log))
        try:
            result = func()
            log = {"stage": stage, "attempt": attempt, "status": "success"}
            print(json.dumps(log))
            return result
        except Exception as e:
            last_exception = e
            _retry_count += 1
            log = {"stage": stage, "attempt": attempt, "status": "failed", "error": str(e)}
            print(json.dumps(log))
            if attempt > max_retries:
                log = {"stage": stage, "attempt": attempt, "status": "abort"}
                print(json.dumps(log))
                sys.exit(1)
    # unreachable
    raise last_exception

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
    return {
        "processed_count": len(cleaned),
        "rejected_count": len(rejected),
        "retry_count": _retry_count,
        "source_files": [input_path]
    }
