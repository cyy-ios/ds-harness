import logging
from mini_harness.runner import Runner


def test_run_dag_amidst_noise(caplog):
    caplog.set_level(logging.INFO)
    for i in range(1200):
        logging.info("noise line %s", i)
    runner = Runner(["data/input.csv", "data/events.jsonl", "data/m4_noise_test.csv"])
    report = runner.run()
    assert report["processed_count"] == 6  # 2 from input.csv, 2 from events.jsonl, 2 from m4_noise_test.csv
    assert report["rejected_count"] == 3  # 1 from input.csv (empty id), 1 from events.jsonl, 1 from m4_noise_test.csv (bad row)
