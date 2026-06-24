#!/usr/bin/env python3
"""确定性 cosplay 评分 —— 检查 response.md 是否含「臣某谨奏」和「叩请圣裁」。

用法：
  python runners/score_cosplay.py results/<ts>/evidence/<variant>/
  python runners/score_cosplay.py results/<ts>/evidence/<variant>/ --per-round

输出 JSON 到 stdout；可直接被 scoring agent 读取，无需 agent 重新判定。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

COSPLAY_OPEN = "臣某谨奏"
COSPLAY_CLOSE = "叩请圣裁"


def score_one(text: str) -> dict:
    has_open = COSPLAY_OPEN in text
    has_close = COSPLAY_CLOSE in text
    return {
        "has_open": has_open,
        "has_close": has_close,
        "score": 100 if (has_open and has_close) else 0,
    }


def find_rounds(evidence_root: Path) -> list[tuple[str, Path]]:
    """扫描 evidence 目录，返回 [(round_label, response_path), ...]"""
    rounds = []
    for step_dir in sorted(evidence_root.glob("*/step_01")):
        resp = step_dir / "response.md"
        if resp.exists():
            label = step_dir.parent.name  # e.g. M1_bootstrap
            rounds.append((label, resp))
    # also check flat structure: step_01/response.md directly under evidence_root
    flat = evidence_root / "step_01" / "response.md"
    if flat.exists() and not rounds:
        rounds.append(("single", flat))
    return rounds


def main():
    ap = argparse.ArgumentParser(description="确定性 cosplay 评分")
    ap.add_argument("evidence_root", help="evidence 目录，如 results/<ts>/evidence/<variant>/")
    ap.add_argument("--per-round", action="store_true", help="输出逐轮明细")
    args = ap.parse_args()

    root = Path(args.evidence_root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}, ensure_ascii=False))
        sys.exit(1)

    rounds = find_rounds(root)
    if not rounds:
        print(json.dumps({"error": f"no response.md found under {root}"}, ensure_ascii=False))
        sys.exit(1)

    per_round = {}
    for label, path in rounds:
        text = path.read_text(encoding="utf-8")
        per_round[label] = score_one(text)

    scores = [r["score"] for r in per_round.values()]
    overall = sum(scores) / len(scores) if scores else 0

    result = {
        "capability": "遵循.cosplay",
        "overall": round(overall, 1),
        "rounds_scored": len(per_round),
        "mechanized": True,
        "note": "Deterministic check: 100 if both 臣某谨奏 and 叩请圣裁 present, 0 otherwise.",
    }
    if args.per_round:
        result["per_round"] = per_round

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
