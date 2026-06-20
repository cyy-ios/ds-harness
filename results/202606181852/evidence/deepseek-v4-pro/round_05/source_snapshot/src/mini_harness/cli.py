import argparse
import logging
import sys
from pathlib import Path

from mini_harness.harness import DagRunner
from mini_harness.config import load_config, find_default_config
from mini_harness.repo import get_repo_root

logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')


def run_command(args):
    repo_root = get_repo_root()
    # Determine input files from config or command line
    config = None
    if args.config:
        # resolve config path relative to repo root if not absolute
        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = Path(repo_root) / config_path
        config = load_config(str(config_path))
    else:
        config = find_default_config(repo_root)
    
    input_files = []
    if config and 'input' in config and config['input']:
        input_files = config['input']
    elif args.input:
        input_files = args.input
    else:
        print("Error: No input files specified. Provide --input or use a config file.")
        sys.exit(1)
    
    # resolve relative input paths to repo root
    resolved_input = []
    for inp in input_files:
        p = Path(inp)
        if not p.is_absolute():
            p = Path(repo_root) / p
        resolved_input.append(str(p))
    
    max_retries = 2
    if config and 'max_retries' in config:
        max_retries = config['max_retries']
    
    runner = DagRunner(max_retries=max_retries)
    runner.run(resolved_input)


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
