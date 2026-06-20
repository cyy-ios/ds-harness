import logging
import tempfile
import os

def test_run_dag_amidst_noise(caplog):
    caplog.set_level(logging.INFO)
    for i in range(1200):
        logging.info("noise line %s", i)
    from mini_harness.runner import run_dag
    # Create temporary data files
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "input.csv")
        with open(csv_path, 'w') as f:
            f.write("id,name,value\n1,Alice,10\n2,Bob,20\n,Charlie,30\n4,Dave,40\n5,Eve,50\n,Frank,60\n7,Grace,70\n,Hank,80\n")
        jsonl_path = os.path.join(tmpdir, "events.jsonl")
        with open(jsonl_path, 'w') as f:
            pass  # empty
        result = run_dag([csv_path, jsonl_path])
    assert result["processed_count"] == 5
    assert result["rejected_count"] == 3
