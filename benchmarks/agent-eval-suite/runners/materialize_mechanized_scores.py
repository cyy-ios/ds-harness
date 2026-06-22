import argparse
import json
import subprocess
import sys
from pathlib import Path

RUNNERS = Path(__file__).resolve().parent

MECHANIZED_FILES = {
    "cosplay": "score_cosplay.json",
    "concise": "score_concise.json",
    "single_instruction": "score_instructions.json",
    "tool_selection": "score_expected_tools.json",
}

SCORERS = {
    "score_cosplay.json": "score_cosplay.py",
    "score_concise.json": "score_concise.py",
    "score_instructions.json": "score_instructions.py",
    "score_expected_tools.json": "score_expected_tools.py",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_mechanized_file(evidence_root: Path, filename: str) -> None:
    path = evidence_root / filename
    if path.exists():
        return
    script = RUNNERS / SCORERS[filename]
    cp = subprocess.run(
        [sys.executable, str(script), str(evidence_root), "--per-round"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"{script.name} failed: {(cp.stderr or '')[:500]}")
    data = json.loads(cp.stdout or "{}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def round_score(data: dict, round_id: str) -> float:
    return float(data["per_round"][round_id]["score"])


def materialize(evidence_root: Path, scores_dir: Path | None) -> dict:
    for filename in MECHANIZED_FILES.values():
        ensure_mechanized_file(evidence_root, filename)

    cosplay = read_json(evidence_root / MECHANIZED_FILES["cosplay"])
    concise = read_json(evidence_root / MECHANIZED_FILES["concise"])
    single = read_json(evidence_root / MECHANIZED_FILES["single_instruction"])
    tools = read_json(evidence_root / MECHANIZED_FILES["tool_selection"])

    rounds = sorted(set(cosplay["per_round"]) & set(concise["per_round"]) & set(single["per_round"]))
    instruction_per_round = {}
    for round_id in rounds:
        persistent = (round_score(cosplay, round_id) + round_score(concise, round_id)) / 2
        score = persistent * 0.4 + round_score(single, round_id) * 0.6
        instruction_per_round[round_id] = {
            "score": round(score, 1),
            "sub_scores": {
                "持久规则": round(persistent, 1),
                "cosplay": round_score(cosplay, round_id),
                "concise": round_score(concise, round_id),
                "单次指令": round_score(single, round_id),
            },
            "evidence": [
                "score_cosplay.json",
                "score_concise.json",
                "score_instructions.json",
            ],
        }

    instruction_score = {
        "capability": "指令遵循",
        "score": average([v["score"] for v in instruction_per_round.values()]),
        "mechanized": True,
        "replacement": "full_capability",
        "formula": "持久规则 = cosplay*0.5 + concise*0.5; 指令遵循 = 持久规则*0.4 + 单次指令*0.6",
        "per_round": instruction_per_round,
        "rounds_scored": len(instruction_per_round),
        "rounds_excluded": 0,
        "evidence_used": [
            "score_cosplay.json",
            "score_concise.json",
            "score_instructions.json",
        ],
        "reason": "Fully mechanized per scoring-output.md; do not re-judge or override.",
        "deductions": [],
        "evidence_gaps": [],
    }

    tool_per_round = {
        round_id: {
            "score": round_score(tools, round_id),
            "sub_scores": {"1.2_工具选择": round_score(tools, round_id)},
            "evidence": ["score_expected_tools.json"],
        }
        for round_id in sorted(tools["per_round"])
    }
    planning_partial = {
        "capability": "任务规划",
        "mechanized": True,
        "replacement": "sub_item",
        "sub_item": "1.2_工具选择",
        "sub_item_weight": 40,
        "per_round": tool_per_round,
        "evidence_used": ["score_expected_tools.json"],
        "reason": "Mechanized sub-item only; route efficiency remains agent-scored and must be combined by rubric weights.",
    }

    overrides = {
        "mechanized_replacements": {
            "指令遵循": instruction_score,
            "任务规划.1.2_工具选择": planning_partial,
        }
    }
    (evidence_root / "mechanized-overrides.json").write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if scores_dir:
        scores_dir.mkdir(parents=True, exist_ok=True)
        (scores_dir / "指令遵循.score.json").write_text(
            json.dumps(instruction_score, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (scores_dir / "任务规划.mechanized.json").write_text(
            json.dumps(planning_partial, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return overrides


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize mechanized scores into capability replacements.")
    parser.add_argument("evidence_root")
    parser.add_argument("--scores-dir", default=None)
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root).resolve()
    scores_dir = Path(args.scores_dir).resolve() if args.scores_dir else None
    result = materialize(evidence_root, scores_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
