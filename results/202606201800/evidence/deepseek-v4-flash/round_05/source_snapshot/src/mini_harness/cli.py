import argparse
import sys
from pathlib import Path

def run_command(args):
    from .config import load_config
    config = load_config(args.config)
    print(f"Running mini_harness with input: {args.input}")
    print(f"Config: {config}")
    # Placeholder for future implementation

def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    subparsers = parser.add_subparsers(dest='command', required=True)
    run_parser = subparsers.add_parser('run', help='Run the data harness pipeline')
    run_parser.add_argument('input', help='Input file (CSV or JSONL)')
    run_parser.add_argument('--config', type=Path, default=Path('config.json'),
                            help='Path to configuration file (JSON)')
    run_parser.set_defaults(func=run_command)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
