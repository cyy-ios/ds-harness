"""CLI for mini_harness."""
import argparse
import logging
import sys
from .runner import run_pipeline
from .config import load_config

def main():
    parser = argparse.ArgumentParser(description='Mini Data Processing Harness')
    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run data processing pipeline')
    run_parser.add_argument('files', nargs='+', help='Input files (CSV or JSONL)')
    run_parser.add_argument('--config', '-c', dest='config_path', default=None, help='Path to config file (JSON or YAML)')

    args = parser.parse_args()
    if args.command == 'run':
        config = load_config(args.config_path)
        log_level = config.get('log_level', 'INFO').upper()
        logging.basicConfig(level=getattr(logging, log_level, logging.INFO),
                            format='%(asctime)s %(levelname)s %(message)s')
        max_retries = config.get('max_retries', 2)
        report = run_pipeline(args.files, max_retries=max_retries)
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
