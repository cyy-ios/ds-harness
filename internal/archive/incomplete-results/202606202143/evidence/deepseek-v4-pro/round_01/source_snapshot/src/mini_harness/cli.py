import argparse
import csv
import json
import sys
from pathlib import Path

from .cleaning import clean_records


def parse_csv(file_path: Path) -> list[dict]:
    """Parse CSV file into list of dicts."""
    records = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def parse_jsonl(file_path: Path) -> list[dict]:
    """Parse JSONL file into list of dicts."""
    records = []
    with open(file_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def parse_file(file_path: Path) -> list[dict]:
    """Parse file based on extension (csv or jsonl)."""
    ext = file_path.suffix.lower()
    if ext == '.csv':
        return parse_csv(file_path)
    elif ext in ('.jsonl', '.json'):
        return parse_jsonl(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def run_command(args):
    """Implementation of the 'run' subcommand."""
    all_records = []
    for file_str in args.input:
        path = Path(file_str)
        if not path.is_absolute():
            # Resolve relative to current working directory
            path = Path.cwd() / path
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        recs = parse_file(path)
        all_records.extend(recs)
    
    processed, rejected = clean_records(all_records)
    
    # Minimal report
    report = {
        "processed_count": len(processed),
        "rejected_count": len(rejected),
        "retry_count": 0,
        "source_files": [str(f) for f in args.input],
    }
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    else:
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(prog='mini-harness', description='Mini Data Harness')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run subcommand
    run_parser = subparsers.add_parser('run', help='Run the data harness')
    run_parser.add_argument('input', nargs='+', help='Input files (CSV or JSONL)')
    run_parser.add_argument('-o', '--output', help='Output report file (default: stdout)')
    run_parser.set_defaults(func=run_command)
    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
