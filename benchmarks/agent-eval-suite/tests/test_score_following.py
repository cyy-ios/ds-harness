import json
import sys
from pathlib import Path

RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from score_following import score_following  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_score_following_uses_task_authored_checklist(tmp_path):
    root = tmp_path / "evidence"
    step = root / "M1_bootstrap" / "step_01"
    _write_text(step / "tool_events.jsonl", json.dumps({"kind": "tool_call", "tool": "read", "arguments": {"path": "skills/data-harness/SKILL.md"}}, ensure_ascii=False) + "\n")
    _write_json(step / "result.json", {"final_response": "done", "response_protocol": {}})
    _write_json(root / "score_cosplay.json", {"per_round": {"M1_bootstrap": {"score": 100}}})
    _write_json(root / "score_concise.json", {"per_round": {"M1_bootstrap": {"score": 100}}})

    result = score_following(root, write_intermediates=True)

    m1 = result["per_round"]["M1_bootstrap"]
    prompt_score = m1["sub_scores"]["单步遵循"]["children"]["Prompt遵循"]
    assert prompt_score["source"] == "instruction-checklist.json"
    assert prompt_score["score"] < 100
    assert (root / "instruction_checklist_results.json").exists()


def test_score_following_uses_cosplay_and_concise_as_persistent_rule_facts(tmp_path):
    root = tmp_path / "evidence"
    step = root / "M2_config" / "step_01"
    _write_text(step / "tool_events.jsonl", "")
    _write_json(step / "result.json", {"final_response": "long", "response_protocol": {}})
    _write_json(root / "score_cosplay.json", {"per_round": {"M2_config": {"score": 0}}})
    _write_json(root / "score_concise.json", {"per_round": {"M2_config": {"score": 50}}})

    result = score_following(root)

    persistent_rule = result["per_round"]["M2_config"]["sub_scores"]["持久遵循"]["children"]["持久规则遵循"]
    assert persistent_rule["score"] == 25.0
    assert persistent_rule["mechanized_scores"] == [0.0, 50.0]
