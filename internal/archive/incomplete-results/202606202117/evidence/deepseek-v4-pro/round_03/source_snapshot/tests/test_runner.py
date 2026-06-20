import json
import os
import tempfile
from mini_harness.runner import extract, clean, report

def create_csv(content, dir):
    path = os.path.join(dir, 'test.csv')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path

def create_jsonl(content, dir):
    path = os.path.join(dir, 'test.jsonl')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path

def test_extract_csv():
    with tempfile.TemporaryDirectory() as tmp:
        csv_content = "ID,Name\n1,Alice\n2,Bob"
        path = create_csv(csv_content, tmp)
        records = extract(path, 1)
        assert len(records) == 2
        assert records[0] == {'ID': '1', 'Name': 'Alice'}

def test_extract_jsonl():
    with tempfile.TemporaryDirectory() as tmp:
        jsonl_content = '{"ID":"1","Name":"Alice"}\n{"ID":"2","Name":"Bob"}'
        path = create_jsonl(jsonl_content, tmp)
        records = extract(path, 1)
        assert len(records) == 2
        assert records[0] == {"ID": "1", "Name": "Alice"}

def test_clean_basic():
    records = [{'ID': '1', 'User Name': 'Alice'}, {'ID': '2', 'User Name': 'Bob'}]
    processed, rejected = clean(records, 1)
    assert len(processed) == 2
    assert 'id' in processed[0]
    assert 'user_name' in processed[0]
    assert rejected == []

def test_clean_missing_id():
    records = [{'ID': '1', 'User Name': 'Alice'}, {'User Name': 'NoId'}]
    processed, rejected = clean(records, 1)
    assert len(processed) == 1
    assert len(rejected) == 1
    assert processed[0]['id'] == '1'

def test_clean_empty_rows():
    records = [{'ID': '1', 'User Name': 'Alice'}, {'ID': '', 'User Name': ''}]
    # empty row: all values empty
    processed, rejected = clean(records, 1)
    assert len(processed) == 1
    assert rejected == []  # empty row just skipped

def test_report():
    result = report([{'id':1}], [{'id':''}], 1, ['input.csv'])
    assert result['processed_count'] == 1
    assert result['rejected_count'] == 1
    assert result['retry_count'] == 1
    assert result['source_files'] == ['input.csv']
