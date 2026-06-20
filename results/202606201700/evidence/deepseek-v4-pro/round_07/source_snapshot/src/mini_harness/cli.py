import argparse
from .runner import run
from .config import load_config

def main():
    parser = argparse.ArgumentParser(description='Mini Data Harness')
    subparsers = parser.add_subparsers(dest='command')
    run_parser = subparsers.add_parser('run', help='Run data processing')
    run_parser.add_argument('files', nargs='+', help='Input files (CSV/JSONL)')
    run_parser.add_argument('--config', default=None, help='Path to config file (JSON). Defaults to harness.json in current directory if exists.')
    args = parser.parse_args()
    if args.command == 'run':
        config = load_config(args.config)
        run(args.files, config=config)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
