import argparse
import json
import subprocess
import sys
from pathlib import Path

RUNNERS = Path(__file__).resolve().parent
sys.path.insert(0, str(RUNNERS))

from score_following import score_following  # noqa: E402

MECHANIZED_FILES = {
    "cosplay": "score_cosplay.json",
    "concise": "score_concise.json",
    "tool_selection": "score_expected_tools.json",
}

SCORERS = {
    "score_cosplay.json": "score_cosplay.py",
    "score_concise.json": "score_concise.py",
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


def round_score(data: dict, round_id: str) -> float:
    return float(data["per_round"][round_id]["score"])


def materialize(evidence_root: Path, scores_dir: Path | None) -> dict:
    for filename in MECHANIZED_FILES.values():
        ensure_mechanized_file(evidence_root, filename)

    following_score = score_following(evidence_root, write_intermediates=True)
    (evidence_root / "遵循.score.json").write_text(
        json.dumps(following_score, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    tools = read_json(evidence_root / MECHANIZED_FILES["tool_selection"])
    tool_per_round = {
        round_id: {
            "score": round_score(tools, round_id),
            "sub_scores": {"1.2_工具选择": round_score(tools, round_id)},
            "evidence": ["score_expected_tools.json"],
        }
        for round_id in sorted(tools.get("per_round", {}))
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
            "遵循": following_score,
            "任务规划.1.2_工具选择": planning_partial,
        }
    }
    (evidence_root / "mechanized-overrides.json").write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if scores_dir:
        scores_dir.mkdir(parents=True, exist_ok=True)
        (scores_dir / "遵循.score.json").write_text(
            json.dumps(following_score, ensure_ascii=False, indent=2), encoding="utf-8"
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
