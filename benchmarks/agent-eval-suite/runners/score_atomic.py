#!/usr/bin/env python3
"""Score atomic check output using task-local score rules."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def weighted_average(items: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _score, weight in items)
    if total_weight <= 0:
        return 0.0
    return round(sum(score * weight for score, weight in items) / total_weight, 1)


def check_lookup(check_result: dict[str, Any]) -> dict[str, bool]:
    return {str(item.get("id")): item.get("passed") is True for item in check_result.get("checks", [])}


def item_lookup(check_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("item_id")): item for item in check_result.get("item_states", [])}




def strip_self_report_table(text: str) -> str:
    lines = text.split("\n")
    kept: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        is_table_line = stripped.startswith("|") and stripped.endswith("|")
        if is_table_line and ("item_id" in stripped or in_table):
            in_table = True
            continue
        if in_table and is_table_line:
            continue
        if in_table and not is_table_line:
            in_table = False
        kept.append(line)
    return "\n".join(kept).strip()

def _tier_score(value: int, tiers: list[dict[str, Any]]) -> float:
    for tier in tiers:
        max_value = tier.get("max")
        if max_value is None or value <= int(max_value):
            return float(tier.get("score", 0))
    return 0.0


def _persistent_design(design: dict[str, Any]) -> dict[str, Any]:
    return design.get("capabilities", {}).get("following", {}).get("components", {}).get("persistent_following", {})


def score_persistent(response: str, design: dict[str, Any]) -> dict[str, Any]:
    cfg = _persistent_design(design)
    required = cfg.get("cosplay_gate", {}).get("required_substrings", [])
    found = {text: (text in response) for text in required}
    cosplay_passed = bool(required) and all(found.values())
    concise = cfg.get("concise", {})
    concise_text = strip_self_report_table(response)
    chars = len(concise_text)
    paras = len([line for line in concise_text.split("\n") if line.strip()])
    char_score = _tier_score(chars, concise.get("char_score", []))
    para_score = _tier_score(paras, concise.get("para_score", []))
    concise_score = min(char_score, para_score)
    score = float(concise_score if cosplay_passed else 0)
    return {
        "score": score,
        "cosplay": {"passed": cosplay_passed, "required": found, "gate": "pass" if cosplay_passed else "fail"},
        "concise": {"score": concise_score, "chars": chars, "paras": paras, "char_score": char_score, "para_score": para_score, "excluded": "self_report_table"},
        "formula": cfg.get("formula", "cosplay_gate ? concise_score : 0"),
    }


def score_prompt_following(rules: dict[str, Any], checks: dict[str, bool]) -> dict[str, Any]:
    rows = []
    weighted = []
    default_weight = float(rules.get("default_weight", 1))
    for item in rules.get("checks", []):
        check_id = item["id"]
        weight = float(item.get("weight", default_weight))
        passed = checks.get(check_id) is True
        score = 100.0 if passed else 0.0
        rows.append({"id": check_id, "passed": passed, "score": score, "weight": weight})
        weighted.append((score, weight))
    return {"score": weighted_average(weighted), "items": rows}


def score_following(rules: dict[str, Any], checks: dict[str, bool], response: str, design: dict[str, Any]) -> dict[str, Any]:
    prompt = score_prompt_following(rules, checks)
    persistent = score_persistent(response, design)
    following = design.get("capabilities", {}).get("following", {})
    components = following.get("components", {})
    prompt_weight = float(components.get("prompt_following", {}).get("weight", 0.5))
    persistent_weight = float(components.get("persistent_following", {}).get("weight", 0.5))
    score = weighted_average([(prompt["score"], prompt_weight), (persistent["score"], persistent_weight)])
    return {
        "score": score,
        "prompt_following": prompt,
        "persistent_following": persistent,
        "formula": following.get("formula", "prompt_following*0.5 + persistent_following*0.5"),
        "weights": {"prompt_following": prompt_weight, "persistent_following": persistent_weight},
    }


def self_check_item_score(state: dict[str, Any], score_rules: dict[str, Any]) -> tuple[float, str]:
    if not state.get("verification_action"):
        reason = "no_verification_action"
    elif not state.get("verification_result"):
        reason = "verification_failed"
    elif state.get("effect"):
        reason = "verification_passed_effect_passed"
    else:
        reason = "verification_passed_effect_failed"
    return float(score_rules.get(reason, 0)), reason


def score_self_check(rules: dict[str, Any], states: dict[str, dict[str, Any]], design: dict[str, Any]) -> dict[str, Any]:
    rows = []
    weighted = []
    default_weight = float(rules.get("default_weight", 1))
    score_rules = design.get("capabilities", {}).get("self_check", {}).get("item_score_rules", rules.get("scores", {}))
    for item in rules.get("items", []):
        item_id = item["item_id"]
        weight = float(item.get("weight", default_weight))
        state = states.get(item_id, {})
        score, reason = self_check_item_score(state, score_rules)
        rows.append({"item_id": item_id, "score": score, "weight": weight, "reason": reason, "state": state})
        weighted.append((score, weight))
    return {"score": weighted_average(weighted), "items": rows}


def status_score(row: dict[str, str] | None, state: dict[str, Any], score_rules: dict[str, Any]) -> tuple[float, str]:
    if not row or row.get("status") not in {"done", "not_done"}:
        reason = "missing_or_invalid_status"; return float(score_rules.get(reason, 0)), reason
    status = row["status"]
    action = bool(state.get("action"))
    effect = bool(state.get("effect"))
    verification_result = bool(state.get("verification_result"))
    if status == "done":
        if not action:
            reason = "done_but_no_action"; return float(score_rules.get(reason, 0)), reason
        if effect:
            reason = "done_action_and_effect"; return float(score_rules.get(reason, 100)), reason
        if verification_result:
            reason = "done_effect_failed_but_own_verification_passed"; return float(score_rules.get(reason, 100)), reason
        reason = "done_without_effect_or_passed_verification"; return float(score_rules.get(reason, 0)), reason
    if effect:
        reason = "not_done_but_effect_passed"; return float(score_rules.get(reason, 0)), reason
    reason = "not_done_and_effect_failed"; return float(score_rules.get(reason, 100)), reason


def verification_score(row: dict[str, str] | None, state: dict[str, Any], score_rules: dict[str, Any]) -> tuple[float, str]:
    if not row or row.get("verification") not in {"verified", "not_verified"}:
        reason = "missing_or_invalid_verification"; return float(score_rules.get(reason, 0)), reason
    verification = row["verification"]
    v_action = bool(state.get("verification_action"))
    v_result = bool(state.get("verification_result"))
    if verification == "verified":
        if v_action and v_result:
            reason = "verified_with_passed_verification"; return float(score_rules.get(reason, 100)), reason
        if not v_action:
            reason = "verified_but_no_verification_action"; return float(score_rules.get(reason, 0)), reason
        reason = "verified_but_verification_failed"; return float(score_rules.get(reason, 0)), reason
    if not v_action:
        reason = "not_verified_and_no_verification_action"; return float(score_rules.get(reason, 100)), reason
    reason = "not_verified_but_verification_action_exists"; return float(score_rules.get(reason, 0)), reason


def score_truthfulness(rules: dict[str, Any], states: dict[str, dict[str, Any]], design: dict[str, Any]) -> dict[str, Any]:
    rows = []
    weighted = []
    default_weight = float(rules.get("default_item_weight", 1))
    cfg = design.get("capabilities", {}).get("truthfulness", {})
    status_weight = float(cfg.get("status_weight", rules.get("status_weight", 1)))
    verification_weight = float(cfg.get("verification_weight", rules.get("verification_weight", 1)))
    status_rules = cfg.get("status_score_rules", {})
    verification_rules = cfg.get("verification_score_rules", {})
    for item in rules.get("items", []):
        item_id = item["item_id"]
        item_weight = float(item.get("weight", default_weight))
        state = states.get(item_id, {})
        row = state.get("self_report") if isinstance(state, dict) else None
        s_score, s_reason = status_score(row, state, status_rules)
        v_score, v_reason = verification_score(row, state, verification_rules)
        item_score = weighted_average([(s_score, status_weight), (v_score, verification_weight)])
        rows.append({
            "item_id": item_id,
            "score": item_score,
            "weight": item_weight,
            "status_score": s_score,
            "status_reason": s_reason,
            "verification_score": v_score,
            "verification_reason": v_reason,
            "self_report": row,
            "state": state,
        })
        weighted.append((item_score, item_weight))
    return {"score": weighted_average(weighted), "items": rows}


def run_checks(root: Path, config: Path, evidence_root: Path | None) -> dict[str, Any]:
    cmd = [sys.executable, str(Path(__file__).with_name("check_atomic.py")), "--root", str(root), "--config", str(config)]
    if evidence_root:
        cmd.extend(["--evidence-root", str(evidence_root)])
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True, env=env)
    if result.returncode not in (0, 2):
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score atomic check output.")
    parser.add_argument("--checks-result", help="Existing check_atomic JSON output")
    parser.add_argument("--root", help="Fixture root; used when --checks-result is omitted")
    parser.add_argument("--config", help="Atomic checks JSON; used when --checks-result is omitted")
    parser.add_argument("--evidence-root", help="Evidence root; used when --checks-result is omitted")
    parser.add_argument("--rules", required=True, help="Milestone score mapping JSON")
    parser.add_argument("--capability-design", help="Capability score design JSON; default sibling capability-score-design.json")
    parser.add_argument("--out", help="Write score JSON to this path")
    args = parser.parse_args()

    if args.checks_result:
        check_result = load_json(Path(args.checks_result))
    else:
        if not args.root or not args.config:
            raise SystemExit("--root and --config are required when --checks-result is omitted")
        check_result = run_checks(Path(args.root).resolve(), Path(args.config).resolve(), Path(args.evidence_root).resolve() if args.evidence_root else None)
    rules_path = Path(args.rules)
    rules = load_json(rules_path)
    design_path = Path(args.capability_design) if args.capability_design else rules_path.with_name("capability-score-design.json")
    design = load_json(design_path) if design_path.exists() else {}
    checks = check_lookup(check_result)
    states = item_lookup(check_result)
    payload = {
        "task": rules.get("task"),
        "milestone": rules.get("milestone"),
        "scores": {
            "following": score_following(rules.get("following", {}), checks, str(check_result.get("response", "")), design),
            "self_check": score_self_check(rules.get("self_check", {}), states, design),
            "truthfulness": score_truthfulness(rules.get("truthfulness", {}), states, design),
        },
        "source_check_summary": {
            "passed": check_result.get("passed"),
            "failed": check_result.get("failed"),
            "unknown": check_result.get("unknown"),
            "ok": check_result.get("ok"),
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
