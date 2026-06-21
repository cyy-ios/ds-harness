import json
import subprocess
import sys
import unittest
from pathlib import Path

from mini_harness.runner import run_dag


ROOT = Path(__file__).resolve().parents[1]


class MiniHarnessTests(unittest.TestCase):
    def tearDown(self):
        for relative in (
            "tmp/unit-report.json",
            "tmp/cli-report.json",
            "tmp/harness-test.json",
            "tmp/harness-test.yaml",
            "tmp/json-config-report.json",
            "tmp/yaml-config-report.json",
            "tmp/default-config-report.json",
            "harness.json",
        ):
            path = ROOT / relative
            if path.exists():
                path.unlink()

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

    def test_run_uses_explicit_json_config(self):
        config = ROOT / "tmp" / "harness-test.json"
        output = ROOT / "tmp" / "json-config-report.json"
        config.parent.mkdir(exist_ok=True)
        config.write_text(
            json.dumps(
                {
                    "sources": ["data/input.csv", "data/events.jsonl"],
                    "output": "tmp/json-config-report.json",
                }
            ),
            encoding="utf-8",
        )

        report = run_dag(config="tmp/harness-test.json")

        self.assertEqual(report["processed_count"], 4)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["rejected_count"], 2)

    def test_cli_uses_yaml_config(self):
        config = ROOT / "tmp" / "harness-test.yaml"
        output = ROOT / "tmp" / "yaml-config-report.json"
        config.parent.mkdir(exist_ok=True)
        config.write_text(
            "\n".join(
                [
                    "sources:",
                    "  - data/input.csv",
                    "  - data/events.jsonl",
                    "output: tmp/yaml-config-report.json",
                ]
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, "-m", "mini_harness", "run", "--config", "tmp/harness-test.yaml"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(json.loads(result.stdout)["source_files"], ["data/input.csv", "data/events.jsonl"])
        self.assertTrue(output.exists())

    def test_run_uses_default_config_when_present(self):
        config = ROOT / "harness.json"
        config.write_text(
            json.dumps(
                {
                    "sources": ["data/input.csv", "data/events.jsonl"],
                    "output": "tmp/default-config-report.json",
                }
            ),
            encoding="utf-8",
        )

        report = run_dag()

        self.assertEqual(report["processed_count"], 4)
        self.assertTrue((ROOT / "tmp" / "default-config-report.json").exists())


if __name__ == "__main__":
    unittest.main()
