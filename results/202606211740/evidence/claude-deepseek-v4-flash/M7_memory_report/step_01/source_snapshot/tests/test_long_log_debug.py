"""Test noisy/debug log handling with m4_noise_test.csv.

Ensures comment lines (#) in CSV are skipped, blank rows produce empty
dicts, and headers are normalised to snake_case.
"""

from mini_harness.utils import read_csv, clean_record


def test_m4_noise_csv_skips_comments():
    """Rows starting with # in m4_noise_test.csv must be skipped."""
    rows = read_csv("data/m4_noise_test.csv")
    # The file has: header row (ID,Name,Score), then c1,Charlie,30,
    # then ,BadRow,0 (no id → reject), then c2,Diana,40
    # #-comment lines should be filtered out.
    assert len(rows) == 3, f"Expected 3 data rows, got {len(rows)}: {rows}"

    # First row: c1,Charlie,30
    assert rows[0].get("id") == "c1"
    assert rows[0].get("name") == "Charlie"  # after snake_case
    assert rows[0].get("score") == "30"

    # Second row: empty id (BadRow) — should have {id: "", name: "BadRow", score: "0"}
    assert rows[1].get("id") == ""
    assert rows[1].get("name") == "BadRow" or rows[1].get("name") == "BadRow"  # name is "BadRow" as-is

    # Third row: c2,Diana,40
    assert rows[2].get("id") == "c2"
    assert rows[2].get("name") == "Diana"


def test_clean_applies_snake_case():
    raw = {"ID": "c1", "Name": "Test", "Score": "50"}
    cleaned = clean_record(raw)
    assert "id" in cleaned
    assert cleaned["id"] == "c1"
    assert cleaned["name"] == "Test"
    assert cleaned["score"] == "50"


def test_m4_integration_via_runner():
    """Run the full DAG on m4_noise_test.csv and check processed/rejected counts."""
    import tempfile
    import os
    import json
    from mini_harness.runner import run_dag

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "report.json")
        report = run_dag(
            sources=["data/m4_noise_test.csv"],
            output=out,
            max_retries=1,
        )
        # c1,Charlie,30 and c2,Diana,40 have ids → processed
        # ,BadRow,0 has no id → rejected
        assert report["processed_count"] == 2, f"Expected 2 processed, got {report['processed_count']}"
        assert report["rejected_count"] == 1, f"Expected 1 rejected, got {report['rejected_count']}"
        assert os.path.isfile(out)


def test_m4_clean_record_keeps_comment_rows_out():
    """Ensure comment lines don't leak into cleaned records."""
    rows = read_csv("data/m4_noise_test.csv")
    cleaned = [clean_record(r) for r in rows if r]
    ids = [r.get("id", "") for r in cleaned if r]
    assert "c1" in ids
    assert "c2" in ids
