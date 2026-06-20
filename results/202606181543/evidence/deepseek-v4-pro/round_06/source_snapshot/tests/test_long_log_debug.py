import os
import logging

def test_run_dag_amidst_noise(caplog):
    caplog.set_level(logging.INFO)
    for i in range(1200):
        logging.info("noise line %s", i)
    from mini_harness.runner import run_dag
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    result = run_dag([
        os.path.join(data_dir, 'input.csv'),
        os.path.join(data_dir, 'events.jsonl'),
        os.path.join(data_dir, 'm4_noise_test.tsv')
    ])
    assert result["processed_count"] == 6
    assert result["rejected_count"] == 3
