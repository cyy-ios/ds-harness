#!/usr/bin/env python3
"""确定性 concise 评分 —— 基于 result.json 字数和段落数计算 concise 分数。

用法：
  python runners/score_concise.py results/<ts>/evidence/<variant>/
  python runners/score_concise.py results/<ts>/evidence/<variant>/ --per-round

规则：
  concise = min(字符分, 段落分)
  字符分: ≤200→100, ≤400→75, ≤700→50, ≤1200→25, >1200→0
  段落分: ≤2→100, ≤4→75, ≤7→50, ≤12→25, >12→0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def char_score(chars: int) -> int:
    if chars <= 200:
        return 100
    if chars <= 400:
        return 75
    if chars <= 700:
        return 50
    if chars <= 1200:
        return 25
    return 0


def para_score(paras: int) -> int:
    if paras <= 2:
        return 100
    if paras <= 4:
        return 75
    if paras <= 7:
        return 50
    if paras <= 12:
        return 25
    return 0


def score_one(text: str) -> dict:
    chars = len(text)
    paras = len([line for line in text.split("\n") if line.strip()])
    cs = char_score(chars)
    ps = para_score(paras)
    return {
        "chars": chars,
        "paras": paras,
        "char_score": cs,
        "para_score": ps,
        "score": min(cs, ps),
    }


def find_rounds(evidence_root: Path) -> list[tuple[str, str]]:
    rounds = []
    for step_dir in sorted(evidence_root.glob("*/step_01")):
        result_path = step_dir / "result.json"
        if result_path.exists():
            label = step_dir.parent.name
            data = json.loads(result_path.read_text(encoding="utf-8"))
            rounds.append((label, str(data.get("final_response", ""))))
    flat = evidence_root / "step_01" / "result.json"
    if flat.exists() and not rounds:
        data = json.loads(flat.read_text(encoding="utf-8"))
        rounds.append(("single", str(data.get("final_response", ""))))
    return rounds


def main():
    ap = argparse.ArgumentParser(description="确定性 concise 评分")
    ap.add_argument("evidence_root", help="evidence 目录")
    ap.add_argument("--per-round", action="store_true", help="输出逐轮明细")
    args = ap.parse_args()

    root = Path(args.evidence_root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}, ensure_ascii=False))
        sys.exit(1)

    rounds = find_rounds(root)
    if not rounds:
        print(json.dumps({"error": f"no result.json found under {root}"}, ensure_ascii=False))
        sys.exit(1)

    per_round = {}
    for label, text in rounds:
        per_round[label] = score_one(text)

    scores = [r["score"] for r in per_round.values()]
    overall = sum(scores) / len(scores) if scores else 0

    result = {
        "capability": "遵循.concise",
        "overall": round(overall, 1),
        "rounds_scored": len(per_round),
        "mechanized": True,
        "method": "concise = min(char_score, para_score). char_score: ≤200→100, ≤400→75, ≤700→50, ≤1200→25, >1200→0. para_score: ≤2→100, ≤4→75, ≤7→50, ≤12→25, >12→0.",
        "note": "Deterministic check based on character count and paragraph count.",
    }
    if args.per_round:
        result["per_round"] = per_round

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
