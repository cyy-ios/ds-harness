import argparse
import csv
import json
import sys
from pathlib import Path

from .cleaning import clean_records
from .config import load_config


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
    # Load config if provided
    config = {}
    if args.config:
        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = Path.cwd() / config_path
        config = load_config(config_path)
    
    # Determine input files: CLI args take precedence, then config['input_files']
    input_sources = args.input if args.input else config.get('input_files', [])
    if not input_sources:
        print("Error: No input files specified.", file=sys.stderr)
        sys.exit(1)
    # Ensure it's a list if config gave a string
    if isinstance(input_sources, str):
        input_sources = [input_sources]
    
    # Determine output: CLI --output overrides config['output']
    output_target = args.output if args.output else config.get('output')
    
    all_records = []
    for file_str in input_sources:
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
    
    source_files = [str(p) for p in input_sources]
    report = {
        "processed_count": len(processed),
        "rejected_count": len(rejected),
        "retry_count": 0,
        "source_files": source_files,
    }
    if output_target:
        out_path = Path(output_target)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    else:
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(prog='mini-harness', description='Mini Data Harness')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run subcommand
    run_parser = subparsers.add_parser('run', help='Run the data harness')
    run_parser.add_argument('input', nargs='*', help='Input files (CSV or JSONL). If not provided, config input_files used.')
    run_parser.add_argument('-c', '--config', help='Path to JSON or YAML config file')
    run_parser.add_argument('-o', '--output', help='Output report file (default: stdout)')
    run_parser.set_defaults(func=run_command)
    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
