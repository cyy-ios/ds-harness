from mini_harness.harness import DagRunner

def run_dag(input_files):
    runner = DagRunner()
    return runner.run(input_files)
