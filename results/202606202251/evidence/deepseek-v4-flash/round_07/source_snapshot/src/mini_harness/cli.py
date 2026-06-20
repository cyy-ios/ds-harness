import argparse
from pathlib import Path
from mini_harness.config import load_config
from mini_harness.run import run_pipeline
from mini_harness.review import generate_review_report

def main():
    parser = argparse.ArgumentParser(prog='mini-harness')
    subparsers = parser.add_subparsers(dest='command', required=True)
    run_parser = subparsers.add_parser('run', help='Run data pipeline')
    run_parser.add_argument('input', nargs='?', help='Input file (CSV or JSONL)')
    run_parser.add_argument('--output', default='report.json', help='Output report path')
    run_parser.add_argument('--config', help='Path to config file (JSON or YAML)')
    review_parser = subparsers.add_parser('review', help='Generate memory-aware review report')
    review_parser.add_argument('--output', default='review_report.json', help='Output review report path')
    args = parser.parse_args()
    if args.command == 'run':
        config = {}
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                parser.error(f'Config file not found: {args.config}')
            config = load_config(str(config_path))
        input_path = args.input
        if input_path is None:
            input_path = config.get('input')
        if input_path is None:
            parser.error('Input file required, provide as argument or in config')
        output_path = args.output
        if output_path == 'report.json' and 'output' in config:
            output_path = config['output']
        run_pipeline(input_path, output_path)
    elif args.command == 'review':
        generate_review_report(args.output)

if __name__ == '__main__':
    main()
