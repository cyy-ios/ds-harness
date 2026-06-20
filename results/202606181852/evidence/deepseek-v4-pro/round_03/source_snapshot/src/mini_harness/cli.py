import argparse
import logging
import sys
from pathlib import Path

from mini_harness.harness import DagRunner
from mini_harness.config import load_config, find_default_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')


def run_command(args):
    # Determine input files from config or command line
    config = None
    if args.config:
        config = load_config(args.config)
    else:
        config = find_default_config()
    
    input_files = []
    if config and 'input' in config and config['input']:
        input_files = config['input']
    elif args.input:
        input_files = args.input
    else:
        print("Error: No input files specified. Provide --input or use a config file.")
        sys.exit(1)
    
    max_retries = 2
    if config and 'max_retries' in config:
        max_retries = config['max_retries']
    
    runner = DagRunner(max_retries=max_retries)
    runner.run(input_files)


def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    subparsers = parser.add_subparsers(dest='command')
    run_parser = subparsers.add_parser('run', help='Run data processing')
    run_parser.add_argument('--input', nargs='+', help='Input files (csv or jsonl)')
    run_parser.add_argument('--config', help='Path to config file (JSON/YAML)')
    run_parser.set_defaults(func=run_command)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
