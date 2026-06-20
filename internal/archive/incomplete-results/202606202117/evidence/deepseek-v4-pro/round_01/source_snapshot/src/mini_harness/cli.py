import argparse
import sys

def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    sub = parser.add_subparsers(dest='command')
    run_parser = sub.add_parser('run', help='Run the mini harness')
    run_parser.add_argument('--input', required=True, help='Input CSV or JSONL file')
    args = parser.parse_args()
    if args.command == 'run':
        print(f"Running mini harness on {args.input}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
