import argparse
import sys
from mini_harness.pipeline import Pipeline
from mini_harness.config import Config

def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run data processing pipeline')
    run_parser.add_argument('input_files', nargs='*', help='Input data files (CSV or JSONL)')
    run_parser.add_argument('--output-dir', help='Output directory for reports')
    run_parser.add_argument('--config', help='Path to configuration file (JSON or YAML)')

    args = parser.parse_args()
    if args.command == 'run':
        config = {}
        if args.config:
            config = Config.load(args.config)
        input_files = args.input_files if args.input_files else config.get('input_files', [])
        output_dir = args.output_dir if args.output_dir else config.get('output_dir')
        if not input_files:
            parser.error("No input files specified either via arguments or config.")
        if not output_dir:
            parser.error("No output directory specified either via arguments or config.")
        pipeline = Pipeline(input_files, output_dir, config)
        pipeline.run()
    else:
        parser.print_help()
        sys.exit(1)
