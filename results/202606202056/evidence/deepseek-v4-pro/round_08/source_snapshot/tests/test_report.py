"""Tests for report module."""
import os
import tempfile
import json
from mini_harness.report import format_report, write_report_file


def test_format_report_text():
    report = {
        'processed_count': 10,
        'rejected_count': 2,
        'retry_count': 1,
        'source_files': ['a.csv', 'b.jsonl']
    }
    text = format_report(report, format='text')
    assert 'processed_count: 10' in text
    assert 'rejected_count: 2' in text
    assert 'retry_count: 1' in text
    assert "source_files: ['a.csv', 'b.jsonl']" in text


def test_format_report_json():
    report = {'processed_count': 5, 'rejected_count': 0, 'retry_count': 0, 'source_files': []}
    json_output = format_report(report, format='json')
    loaded = json.loads(json_output)
    assert loaded == report


def test_format_report_retro():
    report = {
        'processed_count': 4,
        'rejected_count': 0,
        'retry_count': 2,
        'source_files': ['sample.csv']
    }
    retro = format_report(report, format='retro')
    assert '# Memory-Aware Retrospective Report' in retro
    assert 'processed: 4' in retro or 'Processed: 4' in retro
    assert 'Memory Summary' in retro
    assert 'memory_summary.md' in retro


def test_write_report_file_text():
    report = {'processed_count': 1, 'rejected_count': 2, 'retry_count': 0, 'source_files': ['x.csv']}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'report.txt')
        write_report_file(report, path, format='text')
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert 'processed_count: 1' in content


def test_write_report_file_json():
    report = {'processed_count': 10, 'rejected_count': 5, 'retry_count': 1, 'source_files': ['f.csv']}
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'report.json')
        write_report_file(report, path, format='json')
        with open(path) as f:
            loaded = json.load(f)
        assert loaded == report
