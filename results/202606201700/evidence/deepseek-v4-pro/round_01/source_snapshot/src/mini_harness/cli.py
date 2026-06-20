import argparse
from .runner import run

def main():
    parser = argparse.ArgumentParser(description='Mini Data Harness')
    subparsers = parser.add_subparsers(dest='command')
    run_parser = subparsers.add_parser('run', help='Run data processing')
    run_parser.add_argument('files', nargs='+', help='Input files (CSV/JSONL)')
    args = parser.parse_args()
    if args.command == 'run':
        run(args.files)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
