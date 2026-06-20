import argparse
import logging
import sys
from pathlib import Path

from mini_harness.harness import process_file, generate_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')


def run_command(args):
    source_files = []
    cleaned_total = []
    rejected_total = []
    retry_count = 0
    for filepath in args.input:
        source_files.append(str(Path(filepath).resolve()))
        cleaned, rejected, rcount = process_file(filepath, max_retries=2)
        cleaned_total.extend(cleaned)
        rejected_total.extend(rejected)
        retry_count += rcount
    generate_report(cleaned_total, rejected_total, retry_count, source_files)


def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    subparsers = parser.add_subparsers(dest='command')
    run_parser = subparsers.add_parser('run', help='Run data processing')
    run_parser.add_argument('--input', nargs='+', required=True, help='Input files (csv or jsonl)')
    run_parser.set_defaults(func=run_command)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
