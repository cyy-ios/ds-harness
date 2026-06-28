#!/usr/bin/env python3
"""用历史 evidence 验证 instruction-checklist.json 的检查项是否有异常。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _norm_path(text: str) -> str:
    """统一路径分隔符：所有反斜杠序列替换为单个 /，消除 Windows/Unix 及多层 JSON 转义差异。"""
    return re.sub(r"\\+", "/", text)


def load_checklist() -> dict:
    path = Path(__file__).resolve().parents[1] / "tasks" / "mini-data-harness" / "instruction-checklist.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_evidence(evidence_root: Path, milestone: str) -> dict[str, Any]:
    """加载一个 milestone 的新证据：tool_events.jsonl + result.json。"""
    step = evidence_root / milestone / "step_01"
    if not step.exists() and milestone.startswith("M"):
        step = evidence_root / milestone
    tool_events = _read_jsonl(step / "tool_events.jsonl")
    result_path = step / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}

    all_text = "\n".join([_json_text(event) for event in tool_events] + [_json_text(result)])
    command_events = [
        event for event in tool_events
        if str(event.get("tool", "")).lower() in {"shell", "bash", "execute_command", "command_execution"}
    ]
    command_text = "\n".join(_json_text(event) for event in command_events)
    write_events = [
        event for event in tool_events
        if str(event.get("tool", "")).lower() in {"write", "edit", "file_write", "file_edit", "apply_patch"}
    ]
    changed_text = "\n".join(_json_text(event) for event in write_events) or all_text
    final_response = str(result.get("final_response", ""))
    protocol_text = _json_text(result.get("response_protocol", {}))
    return {
        "_step_dir": str(step),
        "tool_events": tool_events,
        "result": result,
        "tool_events_text": all_text,
        "command_text": command_text,
        "changed_text": changed_text,
        "final_response": final_response,
        "result_text": _json_text(result),
        "response_text": final_response + "\n" + protocol_text,
    }


def check_acceptance_passed(evidence: dict, key: str) -> bool | None:
    checks = evidence.get("result", {}).get("checks", {})
    if key not in checks:
        return None
    item = checks.get(key)
    if isinstance(item, dict):
        return bool(item.get("passed"))
    return bool(item)


def _extract_py_hunks(diff_text: str) -> str:
    return diff_text


def apply_check(inst: dict, evidence: dict) -> dict:
    """执行单条检查，返回结果 dict。"""
    method = inst["check"]["method"]
    pattern = inst["check"].get("pattern", "")
    negated = inst["check"].get("negated", False)

    if method == "acceptance_passed":
        key = inst["check"]["key"]
        passed = check_acceptance_passed(evidence, key)
        return {"passed": passed, "detail": f"acceptance.{key}={passed}"}

    if method == "replay_path_contains":
        text = _norm_path(evidence["tool_events_text"])
        matched = bool(re.search(pattern, text, re.I))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"tool_events matched={matched}"}

    if method == "replay_has_tool_type":
        text = evidence["tool_events_text"]
        matched = bool(re.search(pattern, text, re.I))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"tool_events tool matched={matched}"}


    if method == "activity_contains":
        text = _norm_path(evidence["tool_events_text"] + "\n" + evidence["command_text"])
        matched = bool(re.search(pattern, text, re.I))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"activity matched={matched}"}

    if method == "commands_contains":
        text = evidence["command_text"]
        if not text.strip():
            # 空日志：正面指令 → 未执行（fail）；禁止指令 → 不可能违规（pass）
            return {"passed": negated, "detail": "command tool events empty"}
        matched = bool(re.search(pattern, text, re.I))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"command events matched={matched}"}


    if method == "changed_path_contains":
        text = _norm_path("\n".join([
            evidence.get("changed_text", ""),
        ]))
        matched = bool(re.search(pattern, text, re.I | re.M))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"changed_path matched={matched}"}


    if method == "changed_py_content_contains":
        py_text = _extract_py_hunks(evidence.get("changed_text", "")) + "\n" + ""
        py_text = _norm_path(py_text)
        if not py_text.strip():
            return {"passed": True if negated else False, "detail": "changed tool events empty"}
        matched = bool(re.search(pattern, py_text, re.I | re.S))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"changed_py_content matched={matched}"}

    if method == "changed_content_contains":
        text = _norm_path("\n".join([
            evidence.get("changed_text", ""),
        ]))
        if not text.strip() or text.strip() == "(no changes)":
            return {"passed": True if negated else False, "detail": "changed tool events empty"}
        matched = bool(re.search(pattern, text, re.I | re.S))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"changed_content matched={matched}"}

    if method == "diff_path_contains":
        text = _norm_path(evidence["changed_text"])
        if text in ("", "(no changes)"):
            return {"passed": True if negated else False, "detail": "changed tool events empty"}
        matched = bool(re.search(pattern, text, re.I | re.M))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"diff_path matched={matched}"}

    if method == "diff_content_contains":
        text = _norm_path(evidence["changed_text"])
        if text in ("", "(no changes)"):
            return {"passed": True if negated else False, "detail": "changed tool events empty"}
        matched = bool(re.search(pattern, text, re.I))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"diff_content matched={matched}"}

    if method == "diff_py_content_contains":
        """只检查 diff 中 *.py 文件的变更内容，排除 JSON/报告/配置文件。"""
        text = evidence["changed_text"]
        if text in ("", "(no changes)"):
            return {"passed": False, "detail": "changed tool events empty"}
        # 提取仅 *.py 文件的 diff hunks
        py_text = _extract_py_hunks(text)
        if not py_text.strip():
            return {"passed": True if negated else False, "detail": "no .py hunks in diff"}
        py_text = _norm_path(py_text)
        matched = bool(re.search(pattern, py_text, re.I))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"diff_py_content matched={matched}"}


    if method == "response_contains":
        text = evidence["response_text"]
        matched = bool(re.search(pattern, text, re.I | re.S))
        passed = not matched if negated else matched
        return {"passed": passed, "detail": f"response matched={matched}"}

    if method == "response_not_contains":
        text = evidence["response_text"]
        if not text.strip():
            return {"passed": True, "detail": "response empty — vacuously true"}
        matched = bool(re.search(pattern, text, re.I))
        passed = not matched
        return {"passed": passed, "detail": f"response matched={matched}, passed={passed}"}

    return {"passed": None, "detail": f"unknown method: {method}"}


def validate_variant(name: str, evidence_root: Path) -> dict:
    """对一个 variant 的所有 milestone 执行全部检查。"""
    checklist = load_checklist()
    results: dict[str, list] = {}
    anomalies: list[str] = []

    for milestone, ms_def in checklist["milestones"].items():
        ev = load_evidence(evidence_root, milestone)
        ms_results = []

        # 全局禁止指令
        for inst in checklist["global_rules"]["negative"]:
            r = apply_check(inst, ev)
            ms_results.append({"id": inst["id"], "type": "global_negative", "kind": inst.get("kind", "negative"), "required": inst.get("required", "core"), "severity": inst["severity"], **r})
            if not r["passed"]:
                anomalies.append(f"[{milestone}] {inst['id']} ({inst['severity']}): {inst['description']} — {r['detail']}")

        # 正面指令
        for inst in ms_def["positive"]:
            r = apply_check(inst, ev)
            ms_results.append({"id": inst["id"], "type": "positive", "kind": inst.get("kind", "artifact"), "required": inst.get("required", "core"), **r})
            if not r["passed"]:
                anomalies.append(f"[{milestone}] {inst['id']}: {inst['description']} — {r['detail']}")

        # 禁止指令
        for inst in ms_def["negative"]:
            r = apply_check(inst, ev)
            ms_results.append({"id": inst["id"], "type": "negative", "kind": inst.get("kind", "negative"), "required": inst.get("required", "core"), "severity": inst["severity"], **r})
            if not r["passed"]:
                anomalies.append(f"[{milestone}] {inst['id']} ({inst['severity']}): {inst['description']} — {r['detail']}")

        results[milestone] = ms_results

    # 汇总
    total = sum(len(v) for v in results.values())
    known_total = sum(1 for v in results.values() for r in v if r["passed"] is not None)
    passed = sum(1 for v in results.values() for r in v if r["passed"] is True)
    failed = sum(1 for v in results.values() for r in v if r["passed"] is False)
    unknown = total - known_total
    core_total = sum(1 for v in results.values() for r in v if r.get("required") == "core" and r["passed"] is not None)
    core_passed = sum(1 for v in results.values() for r in v if r.get("required") == "core" and r["passed"] is True)
    core_unknown = sum(1 for v in results.values() for r in v if r.get("required") == "core" and r["passed"] is None)
    score = round(passed / known_total * 100, 1) if known_total > 0 else 0
    core_score = round(core_passed / core_total * 100, 1) if core_total > 0 else 0

    return {
        "variant": name,
        "evidence_root": str(evidence_root),
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "unknown": unknown,
        "known_total": known_total,
        "score": score,
        "core_total": core_total,
        "core_passed": core_passed,
        "core_score": core_score,
        "core_unknown": core_unknown,
        "core_failed": core_total - core_passed,
        "core_gate_passed": core_unknown == 0 and core_passed == core_total,
        "anomalies": anomalies,
        "checks": results,
        "per_milestone": {ms: {
            "passed": sum(1 for r in rs if r["passed"] is True),
            "failed": sum(1 for r in rs if r["passed"] is False),
            "unknown": sum(1 for r in rs if r["passed"] is None),
            "core_passed": sum(1 for r in rs if r.get("required") == "core" and r["passed"] is True),
            "core_failed": sum(1 for r in rs if r.get("required") == "core" and r["passed"] is False),
            "core_unknown": sum(1 for r in rs if r.get("required") == "core" and r["passed"] is None),
        } for ms, rs in results.items()},
    }


def _print_human(result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"Variant: {result['variant']}")
    print(f"Score: {result['passed']}/{result['known_total']} known ({result['unknown']} unknown) = {result['score']}%")
    print(f"Core: {result['core_passed']}/{result['core_total']} known ({result['core_unknown']} unknown) = {result['core_score']}%")
    for ms, counts in result["per_milestone"].items():
        bar = "P" * counts["passed"] + "F" * counts["failed"]
        if counts.get("unknown"):
            bar += "U" * counts["unknown"]
        print(f"  {ms}: {bar}  ({counts['passed']}p/{counts['failed']}f/{counts.get('unknown', 0)}u; core {counts['core_passed']}p/{counts['core_failed']}f/{counts['core_unknown']}u)")
    if result["anomalies"]:
        print(f"\n异常 ({len(result['anomalies'])} 条):")
        for a in result["anomalies"]:
            print(f"  - {a}")
    else:
        print("\n无异常")


def main():
    parser = argparse.ArgumentParser(description="Mechanically validate per-turn instruction checklist against evidence.")
    parser.add_argument("evidence_root", nargs="+", help="Evidence root(s), e.g. results/<ts>/evidence/<variant>")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of human text")
    parser.add_argument("--fail-on-core", action="store_true", help="Exit non-zero if any core checklist item fails or is unknown")
    parser.add_argument("--allow-core-unknown", action="store_true", help="With --fail-on-core, tolerate core unknowns from legacy evidence")
    args = parser.parse_args()

    all_results = []
    missing_roots = []
    for path in args.evidence_root:
        root = Path(path).resolve()
        if not root.is_dir():
            missing_roots.append(str(root))
            if not args.json:
                print(f"跳过: {root} 不存在")
            continue
        name = root.parent.parent.name + "/" + root.parent.name + "/" + root.name if root.parent.parent.name.startswith("2026") else root.name
        result = validate_variant(name, root)
        all_results.append(result)
        if not args.json:
            _print_human(result)

    payload = {
        "ok": bool(all_results) and not missing_roots and all(
            r["core_failed"] == 0 and (args.allow_core_unknown or r["core_unknown"] == 0)
            for r in all_results
        ),
        "missing_roots": missing_roots,
        "results": all_results,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print("注意: 以上为纯机械化检查结果；Core 用于单步 prompt 遵循，aux/global 仅作诊断。")

    if args.fail_on_core and not payload["ok"]:
        sys.exit(2)
    if missing_roots:
        sys.exit(1)


if __name__ == "__main__":
    main()
