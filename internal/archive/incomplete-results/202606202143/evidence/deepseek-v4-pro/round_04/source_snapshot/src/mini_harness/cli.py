import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .runner import Runner


def run_command(args):
    """Implementation of the 'run' subcommand."""
    # Load config if provided
    config = {}
    if args.config:
        config_path = Path(args.config)
        if not config_path.is_absolute():
            config_path = Path.cwd() / config_path
        config = load_config(config_path)
    
    # Determine input files: CLI args take precedence, then config['input_files']
    input_sources = args.input if args.input else config.get('input_files', [])
    if not input_sources:
        print("Error: No input files specified.", file=sys.stderr)
        sys.exit(1)
    # Ensure it's a list if config gave a string
    if isinstance(input_sources, str):
        input_sources = [input_sources]
    
    # Determine output: CLI --output overrides config['output']
    output_target = args.output if args.output else config.get('output')
    
    runner = Runner(input_sources)
    try:
        report = runner.run()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # output logs even on failure?
        if args.log:
            with open(args.log, 'w', encoding='utf-8') as lf:
                json.dump(runner.logs, lf, indent=2)
        sys.exit(1)
    
    # Output structured logs if requested
    if args.log:
        with open(args.log, 'w', encoding='utf-8') as lf:
            json.dump(runner.logs, lf, indent=2)
    
    # Output report
    if output_target:
        out_path = Path(output_target)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    else:
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(prog='mini-harness', description='Mini Data Harness')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # run subcommand
    run_parser = subparsers.add_parser('run', help='Run the data harness')
    run_parser.add_argument('input', nargs='*', help='Input files (CSV or JSONL). If not provided, config input_files used.')
    run_parser.add_argument('-c', '--config', help='Path to JSON or YAML config file')
    run_parser.add_argument('-o', '--output', help='Output report file (default: stdout)')
    run_parser.add_argument('-l', '--log', help='Output structured log file')
    run_parser.set_defaults(func=run_command)
    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
