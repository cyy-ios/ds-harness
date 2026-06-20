from .pipeline import run_pipeline

def run_dag(input_files):
    """Run DAG pipeline and return stats dictionary."""
    stats, _ = run_pipeline(input_files)
    return stats
