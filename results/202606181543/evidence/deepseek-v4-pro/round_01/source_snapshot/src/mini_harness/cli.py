import argparse
from .pipeline import run_pipeline
from .config import load_config

def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    subparsers = parser.add_subparsers(dest='command')
    run_parser = subparsers.add_parser('run', help='Run data harness pipeline')
    run_parser.add_argument('input_files', nargs='*', help='Input files (CSV or JSONL). If not provided, taken from config.')
    run_parser.add_argument('-c', '--config', help='Path to config file (JSON or YAML)')
    run_parser.add_argument('-o', '--output', default=None, help='Output directory (overrides config)')
    run_parser.add_argument('--memory', default=None, help='Path to memory summary (overrides config)')
    args = parser.parse_args()
    if args.command == 'run':
        # Load config if provided
        config_data = {}
        if args.config:
            config_data = load_config(args.config)
        # Merge: CLI args override config
        # Input files: from CLI if given, else from config['input']
        if args.input_files:
            input_files = args.input_files
        else:
            input_files = config_data.get('input', [])
        if not input_files:
            parser.error("No input files provided. Specify as arguments or in config.")
        # Output directory
        output_dir = args.output if args.output is not None else config_data.get('output', 'output')
        # Memory path
        memory_path = args.memory if args.memory is not None else config_data.get('memory', 'memory/memory_summary.md')
        run_pipeline(input_files, output_dir, memory_path)
    else:
        parser.print_help()
