
import logging

def test_run_dag_amidst_noise(caplog):
    caplog.set_level(logging.INFO)
    for i in range(1200):
        logging.info("noise line %s", i)
    from mini_harness.runner import run_dag
    result = run_dag(["data/input.csv", "data/events.jsonl", "data/m4_noise_test.csv"])
    stats = result["final_stats"]
    assert stats["processed_count"] == 6
    assert stats["rejected_count"] == 3
