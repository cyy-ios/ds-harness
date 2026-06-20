import json
import logging
import pytest
from mini_harness.runner import extract, clean, generate_report, run, retry_stage, RetryExceededError

def test_extract_csv(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("ID,Name\n1,Alice\n2,Bob\n", encoding='utf-8')
    records = list(extract(str(csv_path)))
    assert len(records) == 2
    assert records[0]['ID'] == '1'

def test_extract_jsonl(tmp_path):
    jsonl_path = tmp_path / "test.jsonl"
    jsonl_path.write_text('{"id":"1","name":"Alice"}\n{"id":"2","name":"Bob"}\n', encoding='utf-8')
    records = list(extract(str(jsonl_path)))
    assert len(records) == 2
    assert records[0]['id'] == '1'

def test_clean_snake_case():
    data = [{"User Name": "Alice", "ID": "1"}]
    cleaned, rejects = clean(data)
    assert cleaned[0] == {"user_name": "Alice", "id": "1"}
    assert len(rejects) == 0

def test_clean_missing_id():
    data = [{"User Name": "Bad", "ID": ""}]
    cleaned, rejects = clean(data)
    assert len(cleaned) == 0
    assert len(rejects) == 1
    assert rejects[0] == {"user_name": "Bad", "id": ""}

def test_generate_report():
    cleaned = [{"id": "1"}]
    rejects = [{"user_name": "Bad"}]
    report = generate_report(cleaned, rejects, 0, ["f.csv"])
    assert report["processed_count"] == 1
    assert report["rejected_count"] == 1
    assert report["retry_count"] == 0
    assert report["source_files"] == ["f.csv"]
    assert "memory_reference" in report

def test_retry_stage_success():
    @retry_stage("test_stage", max_attempts=2)
    def stage():
        return "success"
    result = stage()
    assert result == "success"
    # retries_used should be 0
    assert stage.retries_used == 0
    assert stage.success

def test_retry_stage_retry_once():
    calls = []
    @retry_stage("test_stage", max_attempts=3)  # 3 attempts, so up to 2 retries
    def stage():
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("first fail")
        return "ok"
    result = stage()
    assert result == "ok"
    assert stage.retries_used == 1  # 1 retry (attempt 1)
    assert stage.success

def test_retry_stage_exceeds():
    @retry_stage("test_stage", max_attempts=2)  # 2 attempts, so 1 retry
    def stage():
        raise RuntimeError("fail")
    with pytest.raises(RetryExceededError):
        stage()
    assert stage.retries_used == 1  # after 2 attempts, retries_used = 1
    assert not stage.success

# Patch to prevent reading memory_summary.md
def test_run_with_config(tmp_path, monkeypatch):
    # create temp csv
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("ID,Name\n1,Alice\n2,Bob\n", encoding='utf-8')
    # dummy memory summary to satisfy generate_report
    monkeypatch.setattr("mini_harness.runner.generate_report", lambda cleaned, rejects, retry, source: {
        "processed_count": len(cleaned),
        "rejected_count": len(rejects),
        "retry_count": retry,
        "source_files": source
    })
    config = {"retry_attempts": 2}
    run([str(csv_path)], config=config)
    # No assertion, just check no exception

if __name__ == "__main__":
    pytest.main([__file__])
