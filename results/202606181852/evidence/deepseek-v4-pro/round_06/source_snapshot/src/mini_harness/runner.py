from mini_harness.harness import DagRunner
from mini_harness.repo import get_repo_root
from pathlib import Path

def run_dag(input_files):
    repo_root = get_repo_root()
    resolved = []
    for f in input_files:
        p = Path(f)
        if not p.is_absolute():
            p = Path(repo_root) / p
        resolved.append(str(p))
    runner = DagRunner()
    return runner.run(resolved)
