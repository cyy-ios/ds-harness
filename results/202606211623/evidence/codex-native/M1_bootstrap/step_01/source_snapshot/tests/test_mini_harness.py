import json
import subprocess
import sys
import unittest
from pathlib import Path

from mini_harness.runner import run_dag


ROOT = Path(__file__).resolve().parents[1]


class MiniHarnessTests(unittest.TestCase):
    def test_run_dag_writes_report(self):
        output = ROOT / "tmp" / "unit-report.json"
        if output.exists():
            output.unlink()

        report = run_dag(["data/input.csv", "data/events.jsonl"], "tmp/unit-report.json")

        self.assertEqual(report["processed_count"], 4)
        self.assertEqual(report["rejected_count"], 2)
        self.assertEqual(report["retry_count"], 0)
        self.assertEqual(report["source_files"], ["data/input.csv", "data/events.jsonl"])
        self.assertEqual([entry["stage"] for entry in report["logs"]], ["extract", "clean", "report"])
        self.assertTrue(output.exists())

    def test_cli_run_writes_report(self):
        output = ROOT / "tmp" / "cli-report.json"
        if output.exists():
            output.unlink()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mini_harness",
                "run",
                "data/input.csv",
                "data/events.jsonl",
                "--output",
                "tmp/cli-report.json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        stdout_report = json.loads(result.stdout)
        file_report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(stdout_report["processed_count"], 4)
        self.assertEqual(file_report["rejected_count"], 2)


if __name__ == "__main__":
    unittest.main()
