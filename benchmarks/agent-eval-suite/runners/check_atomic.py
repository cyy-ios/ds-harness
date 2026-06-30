#!/usr/bin/env python3
"""Generic atomic checker driven by a task-local JSON config."""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

TEXT_EXTENSIONS = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt", ".cfg", ".ini"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def norm_path_text(text: str) -> str:
    return re.sub(r"\\+", "/", text)


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_evidence(evidence_root: Path | None, milestone: str) -> dict[str, Any]:
    if evidence_root is None:
        return {"events": [], "result": {}, "all": "", "commands": "", "paths": "", "response": ""}
    step = evidence_root / milestone / "step_01"
    if not step.exists():
        step = evidence_root / milestone
    events = read_jsonl(step / "tool_events.jsonl")
    result_path = step / "result.json"
    result = read_json(result_path) if result_path.exists() else {}
    response = str(result.get("final_response", ""))
    all_text = "\n".join([json_text(e) for e in events] + [json_text(result)])
    command_events = [
        e for e in events
        if e.get("kind") == "tool_call" and str(e.get("tool", "")).lower() in {"shell", "bash", "execute_command", "command_execution"}
    ]
    commands = "\n".join(command_text(e) for e in command_events)
    return {"events": events, "result": result, "all": norm_path_text(all_text), "commands": norm_path_text(commands), "paths": norm_path_text(all_text), "response": response}


def iter_source_files(root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if patterns and not any(fnmatch.fnmatch(rel, pat) for pat in patterns):
            continue
        files.append(path)
    return files



def command_text(event: dict[str, Any]) -> str:
    args = event.get("arguments")
    if isinstance(args, dict):
        for key in ("command", "cmd", "input"):
            if key in args:
                return str(args.get(key, ""))
    return json_text(args)


def result_passed(event: dict[str, Any]) -> bool:
    if event.get("is_error") is True:
        return False
    if event.get("exit_code") is not None:
        return event.get("exit_code") == 0
    output = event.get("output")
    if isinstance(output, dict):
        if output.get("ok") is False:
            return False
        if output.get("exit_code") is not None:
            return output.get("exit_code") == 0
        if output.get("returncode") is not None:
            return output.get("returncode") == 0
    return event.get("is_error") is not True


def check_ids_passed(check_ids: list[str], lookup: dict[str, bool]) -> bool:
    return bool(check_ids) and all(lookup.get(check_id) is True for check_id in check_ids)


def parse_self_report(response: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    allowed_status = {"done", "not_done"}
    allowed_verification = {"verified", "not_verified"}
    for raw in response.splitlines():
        line = raw.strip()
        if not line.startswith("|") or "---" in line or "item_id" in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        item_id, _item, status, verification = cells[:4]
        if status in allowed_status and verification in allowed_verification:
            rows[item_id] = {"status": status, "verification": verification}
    return rows



def build_item_states(config: dict[str, Any], base_results: list[dict[str, Any]], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    report = parse_self_report(str(evidence.get("response", "")))
    lookup = {str(r.get("id")): r.get("passed") is True for r in base_results}
    states: list[dict[str, Any]] = []
    for item in config.get("self_report_items", []):
        item_id = item["item_id"]
        states.append({
            "item_id": item_id,
            "self_report": report.get(item_id),
            "action": check_ids_passed(item.get("action_checks", []), lookup),
            "effect": check_ids_passed(item.get("effect_checks", []), lookup),
            "verification_action": check_ids_passed(item.get("verification_action_checks", []), lookup),
            "verification_result": check_ids_passed(item.get("verification_result_checks", []), lookup),
            "checks": {
                "action_checks": item.get("action_checks", []),
                "effect_checks": item.get("effect_checks", []),
                "verification_action_checks": item.get("verification_action_checks", []),
                "verification_result_checks": item.get("verification_result_checks", []),
            },
        })
    return states

def check_one(check: dict[str, Any], root: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    method = check["method"]
    pattern = check.get("pattern", "")

    if method in {"any_of", "all_of"}:
        children = check.get("checks", [])
        results = [check_one(child, root, evidence) for child in children]
        passed_values = [result.get("passed") for result in results]
        if method == "any_of":
            passed = any(value is True for value in passed_values)
        else:
            passed = bool(results) and all(value is True for value in passed_values)
        return {
            "passed": passed,
            "detail": f"{method}={passed}; children=" + json_text([
                {"id": child.get("id"), "method": child.get("method"), "passed": result.get("passed"), "detail": result.get("detail")}
                for child, result in zip(children, results)
            ]),
        }

    if method == "evidence_path_contains":
        matched = bool(re.search(pattern, evidence["paths"], re.I | re.M))
        return {"passed": matched, "detail": f"matched={matched}"}

    if method == "evidence_command_matches":
        matched = bool(re.search(pattern, evidence["commands"], re.I | re.S))
        return {"passed": matched, "detail": f"matched={matched}"}

    if method == "evidence_command_result_matches":
        matched_calls = []
        passed_calls = []
        for event in evidence.get("events", []):
            if event.get("kind") != "tool_call":
                continue
            if str(event.get("tool", "")).lower() not in {"shell", "bash", "execute_command", "command_execution"}:
                continue
            if not re.search(pattern, command_text(event), re.I | re.S):
                continue
            call_id = event.get("call_id")
            matched_calls.append(call_id)
            for result in evidence.get("events", []):
                if result.get("kind") == "tool_result" and result.get("call_id") == call_id and result_passed(result):
                    passed_calls.append(call_id)
                    break
        return {"passed": bool(passed_calls), "detail": f"matched_calls={matched_calls}; passed_calls={passed_calls}"}



    if method == "evidence_semantic_assert":
        text_all = evidence.get("all", "")
        command_text_all = evidence.get("commands", "")
        successful_outputs = []
        for event in evidence.get("events", []):
            if event.get("kind") == "tool_result" and result_passed(event):
                successful_outputs.append(json_text(event.get("output", "")))
        success_text = norm_path_text("\n".join(successful_outputs))
        missing = []
        for pat in check.get("must_have", []):
            if not re.search(pat, text_all, re.I | re.S):
                missing.append(pat)
        missing_commands = []
        for pat in check.get("commands_must_have", []):
            if not re.search(pat, command_text_all, re.I | re.S):
                missing_commands.append(pat)
        missing_success = []
        for pat in check.get("successful_output_must_have", []):
            if not re.search(pat, success_text, re.I | re.S):
                missing_success.append(pat)
        forbidden = []
        for pat in check.get("must_not_have", []):
            if re.search(pat, text_all, re.I | re.S):
                forbidden.append(pat)
        passed = not (missing or missing_commands or missing_success or forbidden)
        return {"passed": passed, "detail": f"missing={missing}; missing_commands={missing_commands}; missing_success={missing_success}; forbidden={forbidden}"}

    if method == "evidence_command_semantic_check":
        command_pattern = check.get("command_pattern", pattern)
        command_not_pattern = check.get("command_not_pattern")
        expected_output_pattern = check.get("expected_output_pattern", "")
        lookahead = int(check.get("lookahead_results", 3))
        matched = []
        passed = []
        events = evidence.get("events", [])
        for idx, event in enumerate(events):
            if event.get("kind") != "tool_call":
                continue
            if str(event.get("tool", "")).lower() not in {"shell", "bash", "execute_command", "command_execution"}:
                continue
            cmd_text = command_text(event)
            if not re.search(command_pattern, cmd_text, re.I | re.S):
                continue
            if command_not_pattern and re.search(command_not_pattern, cmd_text, re.I | re.S):
                continue
            call_id = event.get("call_id")
            matched.append(call_id)
            related_outputs = []
            command_passed = False
            for j, result in enumerate(events):
                if result.get("kind") == "tool_result" and result.get("call_id") == call_id:
                    command_passed = result_passed(result)
                    related_outputs.append(json_text(result.get("output", "")))
                    for later in events[j + 1:j + 1 + lookahead * 2]:
                        if later.get("kind") == "tool_result":
                            related_outputs.append(json_text(later.get("output", "")))
                    break
            output_text = norm_path_text("\n".join(related_outputs))
            if command_passed and (not expected_output_pattern or re.search(expected_output_pattern, output_text, re.I | re.S)):
                passed.append(call_id)
        return {"passed": bool(passed), "detail": f"matched_calls={matched}; passed_calls={passed}"}

    if method == "evidence_command_not_matches":
        matched = bool(re.search(pattern, evidence["commands"], re.I | re.S))
        return {"passed": not matched, "detail": f"matched={matched}"}

    if method == "command_exit_zero":
        cwd = root / check.get("cwd", ".")
        result = subprocess.run(
            check["command"], cwd=cwd, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=int(check.get("timeout", 60)), shell=False,
        )
        return {
            "passed": result.returncode == 0,
            "detail": f"exit_code={result.returncode}",
            "stdout_tail": result.stdout[-1000:],
            "stderr_tail": result.stderr[-1000:],
        }

    if method == "file_exists":
        path = root / check["path"]
        return {"passed": path.is_file(), "detail": str(path)}

    if method == "json_valid":
        path = root / check["path"]
        try:
            read_json(path)
        except Exception as exc:
            return {"passed": False, "detail": f"{type(exc).__name__}: {exc}"}
        return {"passed": True, "detail": str(path)}

    if method == "json_has_keys":
        data = read_json(root / check["path"])
        missing = [key for key in check.get("keys", []) if key not in data]
        return {"passed": not missing, "detail": f"missing={missing}"}

    if method == "json_values_equal":
        data = read_json(root / check["path"])
        mismatches = {key: {"expected": val, "actual": data.get(key)} for key, val in check.get("values", {}).items() if data.get(key) != val}
        return {"passed": not mismatches, "detail": f"mismatches={mismatches}"}

    if method == "source_matches":
        matches: list[str] = []
        for path in iter_source_files(root, check.get("include", [])):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(pattern, text, re.I | re.S):
                matches.append(path.relative_to(root).as_posix())
        return {"passed": bool(matches), "detail": f"matches={matches[:20]}"}

    if method == "file_matches":
        path = root / check["path"]
        if not path.is_file():
            return {"passed": False, "detail": f"missing={path}"}
        text = path.read_text(encoding="utf-8", errors="ignore")
        matched = bool(re.search(pattern, text, re.I | re.S))
        return {"passed": matched, "detail": f"matched={matched}"}

    if method == "result_response_matches":
        matched = bool(re.search(pattern, evidence["all"], re.I | re.S))
        return {"passed": matched, "detail": f"matched={matched}"}

    if method == "source_not_matches":
        matches: list[str] = []
        for path in iter_source_files(root, check.get("include", [])):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(pattern, text, re.I):
                matches.append(path.relative_to(root).as_posix())
        return {"passed": not matches, "detail": f"matches={matches[:20]}"}

    return {"passed": None, "detail": f"unknown method: {method}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run task-configured atomic checks.")
    parser.add_argument("--root", required=True, help="Fixture repository root")
    parser.add_argument("--config", required=True, help="Atomic checks JSON config")
    parser.add_argument("--evidence-root", help="Evidence root containing <milestone>/step_01/tool_events.jsonl")
    parser.add_argument("--out", help="Write JSON result to this path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config = read_json(Path(args.config))
    evidence = load_evidence(Path(args.evidence_root).resolve() if args.evidence_root else None, config.get("milestone", ""))

    results = []
    for item in config.get("checks", []):
        try:
            outcome = check_one(item, root, evidence)
        except Exception as exc:
            outcome = {"passed": False, "detail": f"{type(exc).__name__}: {exc}"}
        results.append({k: item.get(k) for k in ("id", "group", "description", "method")} | outcome)
    item_states = build_item_states(config, results, evidence)

    payload = {
        "task": config.get("task"),
        "milestone": config.get("milestone"),
        "root": str(root),
        "passed": sum(1 for r in results if r["passed"] is True),
        "failed": sum(1 for r in results if r["passed"] is False),
        "unknown": sum(1 for r in results if r["passed"] is None),
        "checks": results,
        "item_states": item_states,
        "response": evidence.get("response", ""),
    }
    payload["ok"] = payload["failed"] == 0 and payload["unknown"] == 0

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    if not payload["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
