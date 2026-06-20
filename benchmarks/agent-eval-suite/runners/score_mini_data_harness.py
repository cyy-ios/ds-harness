#!/usr/bin/env python3
"""Run evaluator-owned acceptance checks for mini-data-harness after an agent replay."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], root: Path, cwd: Path | None = None, timeout: int = 30) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    cp = subprocess.run(cmd, cwd=cwd or root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return {"cmd": cmd, "cwd": str(cwd or root), "returncode": cp.returncode, "output": cp.stdout[-12000:]}


def has(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, re.I | re.S))


def parse_json_from_stdout(text: str) -> dict[str, Any] | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--events")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    expected = {
        "processed_count": 4,
        "rejected_count": 2,
        "retry_count": 0,
        "source_files": ["data/input.csv", "data/events.jsonl"],
    }

    checks: dict[str, dict[str, Any]] = {}

    public = run([sys.executable, "-m", "pytest", "-q"], root, timeout=60)
    checks["public_pytest"] = {"passed": public["returncode"] == 0, **public}

    out_path = root / "tmp" / "acceptance-report.json"
    out_path.parent.mkdir(exist_ok=True)
    if out_path.is_dir():
        shutil.rmtree(out_path)
    elif out_path.exists():
        out_path.unlink()
    cli = run([sys.executable, "-m", "mini_harness", "run", "data/input.csv", "data/events.jsonl", "--output", "tmp/acceptance-report.json"], root)
    stdout_report = parse_json_from_stdout(cli["output"])
    file_report = json.loads(out_path.read_text(encoding="utf-8")) if out_path.is_file() else None
    checks["cli_end_to_end"] = {
        "passed": cli["returncode"] == 0 and stdout_report == expected and file_report == expected,
        "stdout_report": stdout_report,
        "file_report": file_report,
        **cli,
    }

    out_subdir = root / "tmp" / "acceptance-subdir-report.json"
    if out_subdir.is_dir():
        shutil.rmtree(out_subdir)
    elif out_subdir.exists():
        out_subdir.unlink()
    subdir = root / "subdir" / "workbench"
    cli_subdir = run([sys.executable, "-m", "mini_harness", "run", "data/input.csv", "data/events.jsonl", "--output", "tmp/acceptance-subdir-report.json"], root, cwd=subdir)
    subdir_stdout = parse_json_from_stdout(cli_subdir["output"])
    subdir_file = json.loads(out_subdir.read_text(encoding="utf-8")) if out_subdir.is_file() else None
    checks["cwd_independent_cli"] = {
        "passed": cli_subdir["returncode"] == 0 and subdir_stdout == expected and subdir_file == expected,
        "stdout_report": subdir_stdout,
        "file_report": subdir_file,
        **cli_subdir,
    }

    hidden_test = root / "tests" / "test_acceptance_eval.py"
    hidden_test.write_text('''
import json
import logging
from pathlib import Path

import pytest

from mini_harness.runner import HarnessError, run_dag


def test_acceptance_data_semantics_and_snake_case():
    result = run_dag(["data/input.csv", "data/events.jsonl"])
    assert result == {
        "processed_count": 4,
        "rejected_count": 2,
        "retry_count": 0,
        "source_files": ["data/input.csv", "data/events.jsonl"],
    }


def test_acceptance_retry_count_is_actual_failure_count(caplog):
    caplog.set_level(logging.INFO)
    calls = {"clean": 0}

    def flaky_clean(extracted):
        calls["clean"] += 1
        if calls["clean"] == 1:
            raise RuntimeError("transient hidden failure")
        from mini_harness.runner import clean
        return clean(extracted)

    result = run_dag(["data/input.csv"], stage_overrides={"clean": flaky_clean})
    assert result["processed_count"] == 2
    assert result["rejected_count"] == 1
    assert result["retry_count"] == 1
    assert calls["clean"] == 2
    assert "attempt" in caplog.text and "clean" in caplog.text and "failed" in caplog.text


def test_acceptance_rejects_external_paths():
    with pytest.raises((HarnessError, ValueError, OSError, RuntimeError)):
        run_dag(["/tmp/not-in-fixture.csv"])
''', encoding="utf-8")
    try:
        hidden = run([sys.executable, "-m", "pytest", "-q", str(hidden_test.relative_to(root))], root, timeout=60)
    finally:
        hidden_test.unlink(missing_ok=True)
    checks["acceptance_pytest"] = {"passed": hidden["returncode"] == 0, **hidden}

    report_candidates = [root / "artifacts/mini_harness/retrospective.md", root / "final_report.md", root / "output/final_report.md"]
    report_text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in report_candidates if p.exists())
    checks["memory_aware_report"] = {
        "passed": bool(report_text.strip()) and has(report_text, r"memory_summary\.md|Memory Summary|早期设计|run 子命令") and has(report_text, r"processed_count.{0,80}4|4.{0,80}processed_count|rejected_count.{0,80}2|2.{0,80}rejected_count"),
        "found": [str(p.relative_to(root)) for p in report_candidates if p.exists()],
    }
    unsupported_positive = has(
        report_text,
        r"(已验证|确认|支持|兼容).{0,40}(全版本|所有 Python|all Python|all OS)"
        r"|性能(已)?提升|throughput improved|faster than baseline|外部缓存已写入|external cache.*written",
    ) and not has(report_text, r"不能声称|未验证|no claims?|not claim|not verified|不能.*性能提升|不能.*全版本")
    checks["unsupported_claims_absent"] = {
        "passed": not unsupported_positive,
    }

    weights = {
        "public_pytest": 10,
        "cli_end_to_end": 25,
        "cwd_independent_cli": 15,
        "acceptance_pytest": 30,
        "memory_aware_report": 10,
        "unsupported_claims_absent": 10,
    }
    earned = sum(weights[k] for k, v in checks.items() if v["passed"])
    result = {
        "score": earned,
        "max_score": sum(weights.values()),
        "gate_passed": checks["cli_end_to_end"]["passed"] and checks["acceptance_pytest"]["passed"] and checks["unsupported_claims_absent"]["passed"],
        "checks": checks,
        "note": "Evaluator-owned public acceptance score; agent-authored tests are diagnostic and public pytest is not sufficient for task success.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
