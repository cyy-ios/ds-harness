
import logging

def test_run_dag_amidst_noise(caplog):
    caplog.set_level(logging.INFO)
    for i in range(1200):
        logging.info("noise line %s", i)
    from mini_harness.runner import run_dag
    result = run_dag(["data/input.csv", "data/events.jsonl"])
    assert result["processed_count"] == 5
    assert result["rejected_count"] == 3
