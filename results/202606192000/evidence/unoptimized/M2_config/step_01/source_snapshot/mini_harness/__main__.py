"""Entry point: python -m mini_harness run ..."""
import sys; sys.dont_write_bytecode = True

from mini_harness.cli import main

if __name__ == "__main__":
    sys.exit(main())
