import json
import os
import subprocess
import sys
from pathlib import Path


def run_cli(*args):
    """Run mini_harness.cli as a subprocess."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(Path("src").resolve())
    return subprocess.run(
        [sys.executable, "-m", "mini_harness.cli"] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )


def test_run_no_args():
    result = run_cli("run")
    assert result.returncode != 0
    assert "No input files" in result.stderr


def test_run_with_input_files():
    result = run_cli("run", "data/input.csv", "data/events.jsonl")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2
    assert report["retry_count"] == 0
    assert len(report["source_files"]) == 2


def test_run_with_config_stdout():
    # Config without output file, so report goes to stdout
    result = run_cli("run", "-c", "test_config_no_output.yaml")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["processed_count"] == 4
    assert report["rejected_count"] == 2


def test_run_config_with_output_file(tmp_path):
    output_file = tmp_path / "out.json"
    # Write a temporary config
    config_file = tmp_path / "config.yaml"
    config_file.write_text(f"input_files:\n- data/input.csv\n- data/events.jsonl\noutput: {output_file}")
    result = run_cli("run", "-c", str(config_file))
    assert result.returncode == 0
    assert output_file.exists()
    with open(output_file) as f:
        report = json.load(f)
    assert report["processed_count"] == 4


def test_run_cli_overrides_config():
    # CLI input should override config input_files.
    # Use custom config without output to get stdout.
    result = run_cli("run", "-c", "test_config_no_output.yaml", "data/input.csv")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["processed_count"] == 2  # Only two valid rows in input.csv alone


def test_run_config_not_found():
    result = run_cli("run", "-c", "nonexistent.yaml")
    assert result.returncode != 0
    assert "Config file not found" in result.stderr


def test_run_file_not_found():
    result = run_cli("run", "data/missing.csv")
    assert result.returncode != 0
    assert "File not found" in result.stderr


def test_run_unsupported_format(tmp_path):
    bad_file = tmp_path / "data.txt"
    bad_file.write_text("id,name\n1,test")
    result = run_cli("run", str(bad_file))
    assert result.returncode != 0
    assert "Unsupported" in result.stderr
