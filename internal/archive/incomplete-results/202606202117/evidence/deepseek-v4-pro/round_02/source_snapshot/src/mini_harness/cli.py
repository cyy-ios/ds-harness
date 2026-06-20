import argparse
import sys
from mini_harness.config import load_config, find_default_config, merge_config, DEFAULT_CONFIG

def main():
    parser = argparse.ArgumentParser(prog='mini_harness')
    sub = parser.add_subparsers(dest='command')

    run_parser = sub.add_parser('run', help='Run the mini harness')
    run_parser.add_argument('--input', help='Input CSV or JSONL file')
    run_parser.add_argument('--config', help='Path to config file (JSON or YAML). Default: config.yaml if present.')

    args = parser.parse_args()

    if args.command == 'run':
        # load configuration
        config = DEFAULT_CONFIG.copy()
        if args.config:
            config_path = args.config
        else:
            config_path = find_default_config()
        if config_path:
            try:
                file_config = load_config(config_path)
                config.update(file_config)
            except Exception as e:
                print(f"Warning: failed to load config {config_path}: {e}")
        # merge CLI args (override)
        config = merge_config(args, config)
        # if input still missing, complain
        if 'input' not in config or not config['input']:
            print("Error: input file not specified (use --input or config file).")
            sys.exit(1)
        print(f"Running mini harness on {config['input']} with config: {config}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
