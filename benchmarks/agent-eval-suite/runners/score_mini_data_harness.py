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


ACCEPTANCE_SCHEMA_VERSION = 2
REQUIRED_CHECK_KEYS = [
    "package_main_exists",
    "runner_exports",
    "public_pytest",
    "cli_end_to_end",
    "config_json_cli",
    "cwd_independent_cli",
    "m4_noise_cli",
    "acceptance_pytest",
    "memory_aware_report",
    "unsupported_claims_absent",
]


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


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def report_matches(report: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    if not isinstance(report, dict):
        return False
    return all(report.get(key) == value for key, value in expected.items())


def report_summary_compatible(report: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    if report is None:
        return True
    if not isinstance(report, dict):
        return False
    return all(report.get(key) == value for key, value in expected.items() if key in report)


def load_turn_gates() -> dict[str, Any]:
    spec = Path(__file__).resolve().parents[1] / "tasks" / "mini-data-harness" / "turn-gates.json"
    if not spec.exists():
        return {}
    return json.loads(spec.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--events")
    ap.add_argument("--round", dest="round_id")
    ap.add_argument("--milestone")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    expected = {
        "processed_count": 4,
        "rejected_count": 2,
        "retry_count": 0,
        "source_files": ["data/input.csv", "data/events.jsonl"],
    }

    checks: dict[str, dict[str, Any]] = {}
    main_candidates = [
        root / "src" / "mini_harness" / "__main__.py",
        root / "mini_harness" / "__main__.py",
    ]
    checks["package_main_exists"] = {
        "passed": any(path.is_file() for path in main_candidates),
        "paths": [str(path.relative_to(root)) for path in main_candidates],
    }
    exports = run([sys.executable, "-c", "from mini_harness.runner import HarnessError, run_dag; print(HarnessError.__name__, callable(run_dag))"], root)
    checks["runner_exports"] = {"passed": exports["returncode"] == 0, **exports}

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
    file_report = load_json_file(out_path)
    checks["cli_end_to_end"] = {
        "passed": cli["returncode"] == 0 and report_summary_compatible(stdout_report, expected) and report_matches(file_report, expected),
        "stdout_report": stdout_report,
        "file_report": file_report,
        **cli,
    }

    config_path = root / "tmp" / "acceptance-config.json"
    config_out = root / "tmp" / "acceptance-config-report.json"
    config_path.write_text(json.dumps({"sources": ["data/input.csv", "data/events.jsonl"], "output": "tmp/acceptance-config-report.json"}, ensure_ascii=False), encoding="utf-8")
    if config_out.exists():
        config_out.unlink()
    config_cli = run([sys.executable, "-m", "mini_harness", "run", "--config", str(config_path.relative_to(root))], root)
    config_report = load_json_file(config_out)
    checks["config_json_cli"] = {
        "passed": config_cli["returncode"] == 0 and report_matches(config_report, expected),
        "file_report": config_report,
        **config_cli,
    }

    out_subdir = root / "tmp" / "acceptance-subdir-report.json"
    if out_subdir.is_dir():
        shutil.rmtree(out_subdir)
    elif out_subdir.exists():
        out_subdir.unlink()
    subdir = root / "subdir" / "workbench"
    cli_subdir = run([sys.executable, "-m", "mini_harness", "run", "data/input.csv", "data/events.jsonl", "--output", "tmp/acceptance-subdir-report.json"], root, cwd=subdir)
    subdir_stdout = parse_json_from_stdout(cli_subdir["output"])
    subdir_file = load_json_file(out_subdir)
    checks["cwd_independent_cli"] = {
        "passed": cli_subdir["returncode"] == 0 and report_summary_compatible(subdir_stdout, expected) and report_matches(subdir_file, expected),
        "stdout_report": subdir_stdout,
        "file_report": subdir_file,
        **cli_subdir,
    }

    m4_out = root / "tmp" / "acceptance-m4-noise-report.json"
    if m4_out.exists():
        m4_out.unlink()
    m4_cli = run([sys.executable, "-m", "mini_harness", "run", "data/m4_noise_test.csv", "--output", "tmp/acceptance-m4-noise-report.json"], root)
    m4_report = load_json_file(m4_out)
    checks["m4_noise_cli"] = {
        "passed": m4_cli["returncode"] == 0 and isinstance(m4_report, dict) and m4_report.get("processed_count") == 2 and m4_report.get("rejected_count") == 1,
        "file_report": m4_report,
        **m4_cli,
    }

    hidden_test = root / "tests" / "test_acceptance_eval.py"
    hidden_test.write_text('''
import inspect
import logging

import pytest

from mini_harness.runner import HarnessError, run_dag

EXPECTED = {
    "processed_count": 4,
    "rejected_count": 2,
    "retry_count": 0,
    "source_files": ["data/input.csv", "data/events.jsonl"],
}


def _call_run_dag(paths, **kwargs):
    sig = inspect.signature(run_dag)
    call_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    if "output" in sig.parameters and "output" not in call_kwargs:
        call_kwargs["output"] = "tmp/hidden-acceptance-report.json"
    return run_dag(paths, **call_kwargs)


def _assert_required_report_fields(report, expected):
    for key, value in expected.items():
        assert report.get(key) == value


def test_acceptance_data_semantics_and_snake_case():
    result = _call_run_dag(["data/input.csv", "data/events.jsonl"])
    _assert_required_report_fields(result, EXPECTED)


def test_acceptance_retry_count_is_actual_failure_count(caplog):
    if "stage_overrides" not in inspect.signature(run_dag).parameters:
        pytest.skip("run_dag stage_overrides hook is optional unless exposed by the implementation")
    caplog.set_level(logging.INFO)
    calls = {"clean": 0}

    def flaky_clean(extracted):
        calls["clean"] += 1
        if calls["clean"] == 1:
            raise RuntimeError("transient hidden failure")
        from mini_harness.runner import clean
        return clean(extracted)

    result = _call_run_dag(["data/input.csv"], stage_overrides={"clean": flaky_clean})
    assert result["processed_count"] == 2
    assert result["rejected_count"] == 1
    assert result["retry_count"] == 1
    assert calls["clean"] == 2
    assert "attempt" in caplog.text and "clean" in caplog.text and "failed" in caplog.text


def test_acceptance_rejects_external_paths():
    with pytest.raises((HarnessError, ValueError, OSError, RuntimeError)):
        _call_run_dag(["/tmp/not-in-fixture.csv"])
''', encoding="utf-8")
    try:
        hidden = run([sys.executable, "-m", "pytest", "-q", str(hidden_test.relative_to(root))], root, timeout=60)
    finally:
        hidden_test.unlink(missing_ok=True)
    checks["acceptance_pytest"] = {"passed": hidden["returncode"] == 0, **hidden}

    report_candidates = [
        root / "artifacts/mini_harness/retrospective.md",
        root / "final_report.md",
        root / "output/final_report.md",
        root / "docs/memory_aware_report.md",
        root / "docs/memory-aware-retrospective.md",
        root / "memory/retrospective-report.json",
    ]
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
    earned = sum(weight for k, weight in weights.items() if checks[k]["passed"])
    core_gate_passed = (
        checks["cli_end_to_end"]["passed"]
        and checks["acceptance_pytest"]["passed"]
        and checks["unsupported_claims_absent"]["passed"]
    )
    full_acceptance_passed = all(checks[k]["passed"] for k in weights)
    final_gate_applicable = args.milestone == "M8_compact_resume" or args.round_id == "round_08"
    stage = "final" if final_gate_applicable else "progress_diagnostic"
    turn_gates = load_turn_gates()
    turn_spec = turn_gates.get(args.milestone or "", {})
    turn_required = turn_spec.get("auto_required_checks", [])
    turn_gate_applicable = bool(turn_required)
    turn_missing = [k for k in turn_required if k not in checks]
    turn_failed = [k for k in turn_required if k in checks and not checks[k]["passed"]]
    turn_gate_passed = turn_gate_applicable and not turn_missing and not turn_failed
    result = {
        "score": earned,
        "max_score": sum(weights.values()),
        "round": args.round_id,
        "milestone": args.milestone,
        "stage": stage,
        "gate_scope": stage,
        "gate_passed": core_gate_passed,
        "diagnostic_gate_passed": core_gate_passed,
        "core_gate_passed": core_gate_passed,
        "full_acceptance_passed": full_acceptance_passed,
        "turn_gate_applicable": turn_gate_applicable,
        "turn_gate_passed": turn_gate_passed if turn_gate_applicable else None,
        "turn_required_checks": turn_required,
        "turn_failed_checks": turn_failed,
        "turn_missing_checks": turn_missing,
        "turn_gate_spec": turn_spec,
        "final_gate_applicable": final_gate_applicable,
        "final_gate_passed": full_acceptance_passed if final_gate_applicable else None,
        "acceptance_schema_version": ACCEPTANCE_SCHEMA_VERSION,
        "required_check_keys": REQUIRED_CHECK_KEYS,
        "missing_check_keys": [k for k in REQUIRED_CHECK_KEYS if k not in checks],
        "checks": checks,
        "note": (
            "Evaluator-owned acceptance diagnostics. turn_gate_passed is the prompt-specific gate for this round. "
            "In progress rounds, diagnostic_gate_passed/core_gate_passed are evidence only; "
            "treat final_gate_passed as the full final gate only when final_gate_applicable is true. "
            "Agent-authored tests are diagnostic and public pytest is not sufficient for task success."
        ),
    }
    missing_check_keys = [k for k in REQUIRED_CHECK_KEYS if k not in checks]
    if missing_check_keys:
        result["schema_error"] = f"missing required checks: {missing_check_keys}"
        result["missing_check_keys"] = missing_check_keys
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
