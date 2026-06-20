import argparse
from mini_harness.run import run_pipeline

def main():
    parser = argparse.ArgumentParser(prog='mini-harness')
    subparsers = parser.add_subparsers(dest='command', required=True)
    run_parser = subparsers.add_parser('run', help='Run data pipeline')
    run_parser.add_argument('input', help='Input file (CSV or JSONL)')
    run_parser.add_argument('--output', default='report.json', help='Output report path')
    args = parser.parse_args()
    if args.command == 'run':
        run_pipeline(args.input, args.output)

if __name__ == '__main__':
    main()
