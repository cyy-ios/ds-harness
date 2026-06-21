"""Tests for the report module — output fields, file writing, edge cases."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mini_harness.report import generate_report

TMP_DIR = Path(__file__).resolve().parent.parent / "tmp"


def test_generate_report_writes_file():
    output = str(TMP_DIR / "test-unit-report.json")
    report = generate_report(
        cleaned=[{"id": "1", "name": "Alice"}],
        rejects=[{"name": "no_id_row"}],
        retry_count=0,
        source_files=["data/input.csv"],
        output_path=output,
    )
    assert os.path.exists(output)
    with open(output, "r", encoding="utf-8") as f:
        written = json.load(f)
    assert written == report


def test_generate_report_required_fields():
    output = str(TMP_DIR / "test-unit-fields.json")
    report = generate_report(
        cleaned=[],
        rejects=[],
        retry_count=3,
        source_files=["a.csv", "b.jsonl"],
        output_path=output,
    )
    assert report["processed_count"] == 0
    assert report["rejected_count"] == 0
    assert report["retry_count"] == 3
    assert report["source_files"] == ["a.csv", "b.jsonl"]
    assert "records" in report
    assert "rejected" in report["records"]


def test_generate_report_empty_inputs():
    output = str(TMP_DIR / "test-unit-empty.json")
    report = generate_report(
        cleaned=[],
        rejects=[],
        retry_count=0,
        source_files=[],
        output_path=output,
    )
    assert report["processed_count"] == 0
    assert report["rejected_count"] == 0
    assert report["source_files"] == []
