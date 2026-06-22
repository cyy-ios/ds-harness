#!/usr/bin/env python3
"""确定性单次指令评分 —— 根据 instruction-checklist.json 逐轮计算。

用法：
  python runners/score_instructions.py results/<ts>/evidence/<variant>/
  python runners/score_instructions.py results/<ts>/evidence/<variant>/ --per-round

规则（来自 capability-scoring.md）：
  正面完成率=100% + 无禁止 → 100
  正面完成率≥75% + 无禁止 → 75
  正面完成率<75% + 无禁止 → 50
  任意完成率 + 普通禁止触犯 → 25
  任意完成率 + 关键禁止触犯 → 0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 复用 validate_checklist 的检查引擎
from validate_checklist import (
    load_checklist,
    load_evidence,
    apply_check,
)


def score_milestone(milestone: str, evidence: dict, checklist: dict) -> dict:
    """对一个 milestone 执行所有指令检查并计算单次指令分数。"""
    ms_def = checklist["milestones"][milestone]
    positive_results = []
    negative_results = []

    # 全局禁止指令
    for inst in checklist["global_rules"]["negative"]:
        r = apply_check(inst, evidence)
        negative_results.append({"id": inst["id"], "severity": inst["severity"], **r})

    # 正面指令
    for inst in ms_def["positive"]:
        r = apply_check(inst, evidence)
        positive_results.append({"id": inst["id"], **r})

    # 禁止指令
    for inst in ms_def["negative"]:
        r = apply_check(inst, evidence)
        negative_results.append({"id": inst["id"], "severity": inst["severity"], **r})

    # 计算正面完成率
    total_pos = len(positive_results)
    passed_pos = sum(1 for r in positive_results if r["passed"])
    completion_rate = passed_pos / total_pos if total_pos > 0 else 1.0

    # 判定禁止触犯等级
    critical_violation = any(
        not r["passed"] and r.get("severity") == "关键"
        for r in negative_results
    )
    normal_violation = any(
        not r["passed"] and r.get("severity") == "普通"
        for r in negative_results
    )

    # 查表打分
    if critical_violation:
        score = 0
    elif normal_violation:
        score = 25
    elif completion_rate >= 1.0:
        score = 100
    elif completion_rate >= 0.75:
        score = 75
    else:
        score = 50

    return {
        "score": score,
        "completion_rate": round(completion_rate, 2),
        "positive_passed": passed_pos,
        "positive_total": total_pos,
        "critical_violation": critical_violation,
        "normal_violation": normal_violation,
        "positive_details": [
            {"id": r["id"], "passed": r["passed"], "detail": r["detail"]}
            for r in positive_results
        ],
        "negative_details": [
            {"id": r["id"], "passed": r["passed"], "severity": r["severity"], "detail": r["detail"]}
            for r in negative_results
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="确定性单次指令评分")
    ap.add_argument("evidence_root", help="evidence 目录")
    ap.add_argument("--per-round", action="store_true", help="输出逐轮明细")
    args = ap.parse_args()

    root = Path(args.evidence_root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}, ensure_ascii=False))
        sys.exit(1)

    checklist = load_checklist()

    # 发现所有 milestone
    milestones = sorted(
        {d.parent.name for d in root.glob("*/step_01") if (d / "response.md").exists()}
    )
    if not milestones:
        print(json.dumps({"error": f"no milestone evidence found under {root}"}, ensure_ascii=False))
        sys.exit(1)

    per_round = {}
    for ms in milestones:
        evidence = load_evidence(root, ms)
        per_round[ms] = score_milestone(ms, evidence, checklist)

    scores = [r["score"] for r in per_round.values()]
    overall = sum(scores) / len(scores) if scores else 0

    result = {
        "capability": "指令遵循.单次指令",
        "overall": round(overall, 1),
        "rounds_scored": len(per_round),
        "mechanized": True,
        "method": "completion_rate vs prohibition severity matrix from capability-scoring.md",
        "note": "Deterministic check using instruction-checklist.json. 0=critical violation, 25=normal violation, 50=<75% completion, 75=≥75% completion, 100=100% completion no violations.",
    }
    if args.per_round:
        result["per_round"] = per_round

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
