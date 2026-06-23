import argparse
import logging
from mini_harness.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(prog="mini_harness")
    subparsers = parser.add_subparsers(dest="command")
    
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", nargs="+", required=True, help="Input files (CSV or JSONL)")
    run_parser.add_argument("--output", default="report.json", help="Output report file")
    run_parser.add_argument("--config", help="Optional config file")
    run_parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))
    
    if args.command == "run":
        run_pipeline(args.input, args.output, args.config)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
