import argparse
import logging
from mini_harness.pipeline import run_pipeline
from mini_harness.config import Config

def main():
    parser = argparse.ArgumentParser(prog="mini_harness")
    subparsers = parser.add_subparsers(dest="command")
    
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("input", nargs="+", help="Input files (CSV or JSONL)")
    run_parser.add_argument("--output", help="Output report file")
    run_parser.add_argument("--config", help="Optional config file")
    run_parser.add_argument("--log-level", help="Logging level")
    
    args = parser.parse_args()
    
    # Load config from file if provided, else defaults
    if args.config:
        config = Config.from_file(args.config)
    else:
        config = Config()
    
    # Override with CLI arguments if explicitly provided
    if args.output:
        config.values["output"] = args.output
    if args.log_level:
        config.values["log_level"] = args.log_level
    
    logging.basicConfig(level=getattr(logging, config.values.get("log_level", "INFO").upper()))
    
    if args.command == "run":
        run_pipeline(args.input, config)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
