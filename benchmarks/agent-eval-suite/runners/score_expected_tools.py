#!/usr/bin/env python3
"""机械化工具选择评分 —— 检查每轮是否调用了 tool-checklist.json 中列出的期望工具。

用法：
  python runners/score_expected_tools.py results/<ts>/evidence/<variant>/
  python runners/score_expected_tools.py results/<ts>/evidence/<variant>/ --per-round

规则：
  每轮工具使用率 = 实际使用的期望工具数 / 总期望工具数
  空清单 → 100（不扣分）
  =100% → 100, ≥75% → 75, ≥50% → 50, ≥25% → 25, <25% → 0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_tool_checklist() -> dict:
    path = Path(__file__).resolve().parents[1] / "tasks" / "mini-data-harness" / "tool-checklist.json"
    return json.loads(path.read_text(encoding="utf-8"))


def extract_tools_used(replay_text: str) -> set[str]:
    """从 tool_events.jsonl 提取所有被调用的工具名。"""
    tools = set()
    for line in replay_text.splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        tool = rec.get("tool", "")
        if tool:
            tools.add(tool)
    return tools


def score_round(replay_text: str, expected: list[str]) -> dict:
    tools_used = extract_tools_used(replay_text)
    expected_set = set(expected)

    if not expected_set:
        return {
            "score": 100,
            "expected": [],
            "used": sorted(tools_used),
            "missing": [],
            "note": "empty expected list — no deduction",
        }

    missing = sorted(expected_set - tools_used)
    found = sorted(expected_set & tools_used)
    ratio = len(found) / len(expected_set)

    if ratio >= 1.0:
        score = 100
    elif ratio >= 0.75:
        score = 75
    elif ratio >= 0.5:
        score = 50
    elif ratio >= 0.25:
        score = 25
    else:
        score = 0

    return {
        "score": score,
        "expected": sorted(expected_set),
        "used": sorted(tools_used),
        "missing": missing,
        "ratio": round(ratio, 2),
    }


def main():
    ap = argparse.ArgumentParser(description="机械化工具选择评分")
    ap.add_argument("evidence_root", help="evidence 目录")
    ap.add_argument("--per-round", action="store_true", help="输出逐轮明细")
    args = ap.parse_args()

    root = Path(args.evidence_root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}, ensure_ascii=False))
        sys.exit(1)

    checklist = load_tool_checklist()
    ms_expected = checklist["milestones"]

    rounds = []
    for step_dir in sorted(root.glob("*/step_01")):
        replay = step_dir / "tool_events.jsonl"
        if replay.exists():
            label = step_dir.parent.name
            text = replay.read_text(encoding="utf-8", errors="replace")
            expected = ms_expected.get(label, [])
            rounds.append((label, text, expected))

    if not rounds:
        print(json.dumps({"error": f"no tool_events.jsonl found under {root}"}, ensure_ascii=False))
        sys.exit(1)

    per_round = {}
    for label, text, expected in rounds:
        per_round[label] = score_round(text, expected)

    scores = [r["score"] for r in per_round.values()]
    overall = sum(scores) / len(scores) if scores else 0

    result = {
        "capability": "任务规划.工具选择",
        "overall": round(overall, 1),
        "rounds_scored": len(per_round),
        "mechanized": True,
        "method": "检查 tool-checklist.json 中每轮期望工具是否被调用。空清单 → 100。",
        "note": "工具选择评的是 agent 是否调用了任务期望的专用工具/Skill，不是 Read vs cat 这类粒度。",
    }
    if args.per_round:
        result["per_round"] = per_round

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
