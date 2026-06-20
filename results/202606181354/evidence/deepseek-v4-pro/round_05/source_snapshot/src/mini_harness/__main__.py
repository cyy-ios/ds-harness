import sys
import os
# Ensure src is in sys.path so that mini_harness can be imported from any working directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from mini_harness.cli import main
main()
