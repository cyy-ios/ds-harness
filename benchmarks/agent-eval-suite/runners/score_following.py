#!/usr/bin/env python3
"""Fixed scorer for the 遵循 capability."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from match_violations import match_violations_for_round

RUNNERS = Path(__file__).resolve().parent
SUB_WEIGHTS = {
    "持久遵循": {"weight": 50, "children": {"持久规则遵循": 40, "持久流程遵循": 30, "局部持久约束遵循": 30}},
    "单步遵循": {"weight": 50, "children": {"Prompt遵循": 30, "单步流程遵循": 70}},
}
SEVERITY_DEDUCT = {
    ("critical", "violated"): 45,
    ("critical", "missing"): 35,
    ("major", "violated"): 25,
    ("major", "missing"): 20,
    ("minor", "violated"): 10,
    ("minor", "missing"): 5,
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _discover_round_dirs(evidence_root: Path) -> list[Path]:
    round_dirs = [p for p in sorted(evidence_root.glob("round_*")) if (p / "prompt.json").exists()]
    if round_dirs:
        return round_dirs
    return [p for p in sorted(evidence_root.glob("*/step_01")) if (p / "prompt.json").exists()]


def _round_label(round_dir: Path, match: dict[str, Any]) -> str:
    milestone = str(match.get("milestone") or "")
    if milestone:
        return milestone
    return round_dir.parent.name if round_dir.name == "step_01" else round_dir.name


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
        # tolerate round_NN labels when scripts use milestone labels or vice versa.
        for key, value in per_round.items():
            if key == label or key.endswith(label) or label.endswith(key):
                item = value
                break
    if isinstance(item, dict) and item.get("score") is not None:
        return float(item["score"])
    return None


def _deduction_for(v: dict[str, Any]) -> int:
    severity = str(v.get("severity") or "major")
    verdict = str(v.get("verdict") or "")
    return SEVERITY_DEDUCT.get((severity, verdict), 0)


def _score_sub_item(
    sub_item: str,
    violations: list[dict[str, Any]],
    *,
    mechanized_scores: list[float],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str]]:
    relevant = [v for v in violations if v.get("sub_item") == sub_item]
    if not relevant and not mechanized_scores:
        return None, [], []
    base = round(sum(mechanized_scores) / len(mechanized_scores), 1) if mechanized_scores else 100.0
    deductions: list[dict[str, Any]] = []
    gaps: list[str] = []
    cap: float | None = None
    for v in relevant:
        verdict = v.get("verdict")
        if verdict == "insufficient_evidence":
            gaps.append(str(v.get("requirement_id") or v.get("requirement_text") or "unknown"))
            continue
        amount = _deduction_for(v)
        if amount <= 0:
            continue
        if v.get("severity") == "critical" and verdict == "violated":
            cap = min(cap if cap is not None else 100, 40)
        elif v.get("severity") == "critical":
            cap = min(cap if cap is not None else 100, 60)
        deductions.append(
            {
                "requirement_id": v.get("requirement_id"),
                "sub_item": sub_item,
                "severity": v.get("severity"),
                "verdict": verdict,
                "amount": amount,
                "reason": v.get("reason"),
                "evidence": v.get("evidence") or [],
            }
        )
    score = max(0.0, base - sum(d["amount"] for d in deductions))
    if cap is not None:
        score = min(score, cap)
    detail = {
        "score": round(score, 1),
        "base_score": base,
        "mechanized_scores": mechanized_scores,
        "requirements": len(relevant),
        "violations": [v for v in relevant if v.get("verdict") in {"violated", "missing"}],
        "deductions": deductions,
        "evidence_gaps": gaps,
    }
    return detail, deductions, gaps


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


def score_following(evidence_root: Path, *, write_intermediates: bool = False) -> dict[str, Any]:
    round_dirs = _discover_round_dirs(evidence_root)
    cosplay = _ensure_score_file(evidence_root, "score_cosplay.json", "score_cosplay.py")
    concise = _ensure_score_file(evidence_root, "score_concise.json", "score_concise.py")
    per_round: dict[str, Any] = {}
    all_deductions: list[dict[str, Any]] = []
    all_gaps: list[str] = []

    for round_dir in round_dirs:
        match = match_violations_for_round(round_dir)
        if write_intermediates:
            (round_dir / "violations.json").write_text(json.dumps(match, ensure_ascii=False, indent=2), encoding="utf-8")
        label = _round_label(round_dir, match)
        violations = match.get("violations") or []
        mech = []
        c1 = _mechanized_round_score(cosplay, label)
        c2 = _mechanized_round_score(concise, label)
        if c1 is not None:
            mech.append(c1)
        if c2 is not None:
            mech.append(c2)

        sub_items: dict[str, dict[str, Any] | None] = {}
        round_deductions: list[dict[str, Any]] = []
        round_gaps: list[str] = []
        for sub in ["持久规则遵循", "持久流程遵循", "局部持久约束遵循", "Prompt遵循", "单步流程遵循"]:
            detail, deds, gaps = _score_sub_item(sub, violations, mechanized_scores=mech if sub == "持久规则遵循" else [])
            sub_items[sub] = detail
            round_deductions.extend(deds)
            round_gaps.extend(f"{label}:{g}" for g in gaps)

        persistent_children = SUB_WEIGHTS["持久遵循"]["children"]
        single_children = SUB_WEIGHTS["单步遵循"]["children"]
        persistent_score = _weighted(sub_items, persistent_children)
        single_score = _weighted(sub_items, single_children)
        group_scores = {
            "持久遵循": {"score": persistent_score, "children": {k: sub_items[k] for k in persistent_children}},
            "单步遵循": {"score": single_score, "children": {k: sub_items[k] for k in single_children}},
        }
        round_score = _weighted(group_scores, {k: int(v["weight"]) for k, v in SUB_WEIGHTS.items()})
        if round_score is None:
            round_score = 100.0
            round_gaps.append(f"{label}:no_applicable_following_requirements")
        per_round[label] = {
            "score": round_score,
            "sub_scores": group_scores,
            "deductions": round_deductions,
            "evidence_gaps": round_gaps,
            "evidence": [str(round_dir / name) for name in ("requirements.json", "behavior_facts.json", "violations.json")],
        }
        for d in round_deductions:
            all_deductions.append({"round": label, **d})
        all_gaps.extend(round_gaps)

    scores = [float(r["score"]) for r in per_round.values()]
    return {
        "capability": "遵循",
        "score": round(sum(scores) / len(scores), 1) if scores else 0,
        "mechanized": True,
        "replacement": "full_capability",
        "formula": "Recursive weighted aggregation from capability-weights.yaml; null sub-items excluded; fixed severity deductions from violations.json; cosplay/concise feed 持久规则遵循.",
        "per_round": per_round,
        "rounds_scored": len(per_round),
        "rounds_excluded": 0,
        "evidence_used": ["requirements.json", "behavior_facts.json", "violations.json", "score_cosplay.json", "score_concise.json"],
        "deductions": all_deductions,
        "evidence_gaps": all_gaps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score 遵循 deterministically.")
    parser.add_argument("evidence_root")
    parser.add_argument("--write", action="store_true", help="Write 遵循.score.json under evidence root and violations.json per round")
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
