"""CLI for mini_harness."""
import argparse
import logging
import sys
from .runner import run_pipeline

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    parser = argparse.ArgumentParser(description='Mini Data Processing Harness')
    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run data processing pipeline')
    run_parser.add_argument('files', nargs='+', help='Input files (CSV or JSONL)')

    args = parser.parse_args()
    if args.command == 'run':
        report = run_pipeline(args.files)
        print_report(report)
    else:
        parser.print_help()
        sys.exit(1)

def print_report(report):
    print(f"processed_count: {report['processed_count']}")
    print(f"rejected_count: {report['rejected_count']}")
    print(f"retry_count: {report['retry_count']}")
    print(f"source_files: {report['source_files']}")

if __name__ == '__main__':
    main()
