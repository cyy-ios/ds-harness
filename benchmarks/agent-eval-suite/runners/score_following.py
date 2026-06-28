#!/usr/bin/env python3
"""Fixed scorer for the 遵循 capability using task-authored checklist points."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from validate_checklist import validate_variant

RUNNERS = Path(__file__).resolve().parent
SUB_WEIGHTS = {
    "持久遵循": {"weight": 50, "children": {"持久规则遵循": 100}},
    "单步遵循": {"weight": 50, "children": {"Prompt遵循": 100}},
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _ensure_score_file(evidence_root: Path, filename: str, script_name: str) -> dict[str, Any]:
    path = evidence_root / filename
    existing = _read_json(path) if path.exists() else {}
    if existing.get("per_round"):
        return existing
    script = RUNNERS / script_name
    if not script.exists():
        return {}
    cp = subprocess.run(
        [sys.executable, str(script), str(evidence_root), "--per-round"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if cp.returncode != 0:
        return {"error": cp.stderr[:500]}
    data = json.loads(cp.stdout or "{}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _mechanized_round_score(data: dict[str, Any], label: str) -> float | None:
    per_round = data.get("per_round") if isinstance(data.get("per_round"), dict) else {}
    item = per_round.get(label)
    if item is None:
        for key, value in per_round.items():
            if key == label or key.endswith(label) or label.endswith(key):
                item = value
                break
    if isinstance(item, dict) and item.get("score") is not None:
        return float(item["score"])
    return None


def _weighted(children: dict[str, dict[str, Any] | None], weights: dict[str, int]) -> float | None:
    total = 0.0
    denom = 0.0
    for name, weight in weights.items():
        child = children.get(name)
        if child is None or child.get("score") is None:
            continue
        total += float(child["score"]) * weight
        denom += weight
    if denom == 0:
        return None
    return round(total / denom, 1)


def _checklist_subscore(label: str, checks: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str]]:
    applicable = [c for c in checks if c.get("required") == "core" and c.get("passed") is not None]
    unknown = [str(c.get("id")) for c in checks if c.get("required") == "core" and c.get("passed") is None]
    if not applicable and not unknown:
        return None, [], []
    passed = sum(1 for c in applicable if c.get("passed") is True)
    score = round(passed / len(applicable) * 100, 1) if applicable else None
    deductions = []
    for c in applicable:
        if c.get("passed") is False:
            deductions.append({
                "requirement_id": c.get("id"),
                "sub_item": "Prompt遵循",
                "severity": "major",
                "verdict": "missing" if c.get("type") == "positive" else "violated",
                "amount": round(100 / len(applicable), 1),
                "reason": c.get("detail"),
                "evidence": [c.get("id")],
            })
    detail = {
        "score": score,
        "source": "instruction-checklist.json",
        "checks": len(applicable),
        "passed": passed,
        "failed": len(applicable) - passed,
        "unknown": unknown,
        "deductions": deductions,
        "evidence_gaps": unknown,
    }
    return detail, deductions, [f"{label}:{u}" for u in unknown]


def _persistent_rule_subscore(cosplay: dict[str, Any], concise: dict[str, Any], label: str) -> dict[str, Any] | None:
    mech = []
    c1 = _mechanized_round_score(cosplay, label)
    c2 = _mechanized_round_score(concise, label)
    if c1 is not None:
        mech.append(c1)
    if c2 is not None:
        mech.append(c2)
    if not mech:
        return None
    return {
        "score": round(sum(mech) / len(mech), 1),
        "base_score": round(sum(mech) / len(mech), 1),
        "mechanized_scores": mech,
        "source": ["score_cosplay.json", "score_concise.json"],
        "deductions": [],
        "evidence_gaps": [],
    }


def score_following(evidence_root: Path, *, write_intermediates: bool = False) -> dict[str, Any]:
    checklist_result = validate_variant(evidence_root.name, evidence_root)
    if write_intermediates:
        (evidence_root / "instruction_checklist_results.json").write_text(json.dumps(checklist_result, ensure_ascii=False, indent=2), encoding="utf-8")
    cosplay = _ensure_score_file(evidence_root, "score_cosplay.json", "score_cosplay.py")
    concise = _ensure_score_file(evidence_root, "score_concise.json", "score_concise.py")

    per_round: dict[str, Any] = {}
    all_deductions: list[dict[str, Any]] = []
    all_gaps: list[str] = []
    all_labels = sorted(set(checklist_result.get("checks", {}).keys()) | set((cosplay.get("per_round") or {}).keys()) | set((concise.get("per_round") or {}).keys()))

    for label in all_labels:
        sub_items: dict[str, dict[str, Any] | None] = {
            "持久规则遵循": _persistent_rule_subscore(cosplay, concise, label),
            "Prompt遵循": None,
        }
        checklist_detail, deds, gaps = _checklist_subscore(label, checklist_result.get("checks", {}).get(label, []))
        sub_items["Prompt遵循"] = checklist_detail

        persistent_children = SUB_WEIGHTS["持久遵循"]["children"]
        single_children = SUB_WEIGHTS["单步遵循"]["children"]
        persistent_score = _weighted(sub_items, persistent_children)
        single_score = _weighted(sub_items, single_children)
        group_scores = {
            "持久遵循": {"score": persistent_score, "children": {k: sub_items.get(k) for k in persistent_children}},
            "单步遵循": {"score": single_score, "children": {k: sub_items.get(k) for k in single_children}},
        }
        round_score = _weighted(group_scores, {k: int(v["weight"]) for k, v in SUB_WEIGHTS.items()})
        if round_score is None:
            round_score = 100.0
            gaps.append(f"{label}:no_applicable_following_checks")
        per_round[label] = {
            "score": round_score,
            "sub_scores": group_scores,
            "deductions": deds,
            "evidence_gaps": gaps,
            "evidence": ["instruction-checklist.json", "instruction_checklist_results.json", "score_cosplay.json", "score_concise.json"],
        }
        for d in deds:
            all_deductions.append({"round": label, **d})
        all_gaps.extend(gaps)

    scores = [float(r["score"]) for r in per_round.values()]
    return {
        "capability": "遵循",
        "score": round(sum(scores) / len(scores), 1) if scores else 0,
        "mechanized": True,
        "replacement": "full_capability",
        "formula": "Task-authored instruction-checklist.json core checks feed Prompt遵循; score_cosplay.json and score_concise.json feed 持久规则遵循; null sub-items excluded.",
        "per_round": per_round,
        "rounds_scored": len(per_round),
        "rounds_excluded": 0,
        "evidence_used": ["instruction-checklist.json", "instruction_checklist_results.json", "score_cosplay.json", "score_concise.json"],
        "deductions": all_deductions,
        "evidence_gaps": all_gaps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score 遵循 from task-authored checklist points.")
    parser.add_argument("evidence_root")
    parser.add_argument("--write", action="store_true", help="Write 遵循.score.json and instruction_checklist_results.json under evidence root")
    parser.add_argument("--per-round", action="store_true", help="Compatibility no-op; output is always per-round")
    parser.add_argument("--scores-dir", default=None, help="Optional scores directory for 遵循.score.json")
    args = parser.parse_args()
    evidence_root = Path(args.evidence_root).resolve()
    if not evidence_root.is_dir():
        print(json.dumps({"error": f"not a directory: {evidence_root}"}, ensure_ascii=False))
        sys.exit(1)
    result = score_following(evidence_root, write_intermediates=args.write)
    if args.write:
        (evidence_root / "遵循.score.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.scores_dir:
        scores_dir = Path(args.scores_dir).resolve()
        scores_dir.mkdir(parents=True, exist_ok=True)
        (scores_dir / "遵循.score.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
