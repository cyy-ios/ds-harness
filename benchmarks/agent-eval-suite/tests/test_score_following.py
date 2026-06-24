import json
import sys
from pathlib import Path

RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from score_following import score_following  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_score_following_outputs_sub_item_scores_and_deductions(tmp_path):
    root = tmp_path / "evidence"
    round_dir = root / "M1_bootstrap" / "step_01"
    _write_json(round_dir / "prompt.json", {"id": "M1_bootstrap", "prompt": "先读取 README.md 再修改 src/app.py；失败时停止并汇报。"})
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {"requirement_id": "r1", "sub_item": "单步流程遵循", "type": "sequence", "scope": "current_turn", "text": "读取 README.md -> 修改 src/app.py", "source": "prompt", "severity": "major"},
                {"requirement_id": "r2", "sub_item": "单步流程遵循", "type": "stop_condition", "scope": "current_turn", "text": "失败时停止并汇报", "source": "prompt", "severity": "major"},
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [{"index": 1, "tool": "edit", "target": "src/app.py"}, {"index": 3, "tool": "read_file", "target": "README.md"}],
            "commands": [{"index": 2, "command": "pytest", "exit_code": 1}, {"index": 4, "command": "python fix.py", "exit_code": 0}],
            "edited_files": [{"path": "src/app.py"}],
            "artifacts": [],
            "final_response": "done",
            "final_claims": [{"text": "done"}],
            "operation_order": [{"tool": "edit", "target": "src/app.py"}, {"tool": "read_file", "target": "README.md"}],
            "failed_steps": [{"index": 2, "command": "pytest", "exit_code": 1}],
            "post_failure_actions": [{"index": 4, "kind": "command", "command": "python fix.py"}],
        },
    )
    _write_json(root / "score_cosplay.json", {"per_round": {"M1_bootstrap": {"score": 100}}})
    _write_json(root / "score_concise.json", {"per_round": {"M1_bootstrap": {"score": 100}}})

    result = score_following(root, write_intermediates=True)

    assert result["capability"] == "遵循"
    round_score = result["per_round"]["M1_bootstrap"]
    assert round_score["sub_scores"]["单步遵循"]["children"]["单步流程遵循"]["score"] < 100
    assert len(round_score["deductions"]) == 2
    assert (round_dir / "violations.json").exists()


def test_score_following_uses_cosplay_and_concise_as_persistent_rule_facts(tmp_path):
    root = tmp_path / "evidence"
    round_dir = root / "M2_config" / "step_01"
    _write_json(round_dir / "prompt.json", {"id": "M2_config", "prompt": "解释当前状态。"})
    _write_json(round_dir / "requirements.json", {"milestone": "M2_config", "requirements": []})
    _write_json(round_dir / "behavior_facts.json", {"milestone": "M2_config", "tool_calls": [], "commands": [], "edited_files": [], "artifacts": [], "final_response": "long", "final_claims": [], "operation_order": []})
    _write_json(root / "score_cosplay.json", {"per_round": {"M2_config": {"score": 0}}})
    _write_json(root / "score_concise.json", {"per_round": {"M2_config": {"score": 50}}})

    result = score_following(root)

    persistent_rule = result["per_round"]["M2_config"]["sub_scores"]["持久遵循"]["children"]["持久规则遵循"]
    assert persistent_rule["score"] == 25.0
    assert persistent_rule["mechanized_scores"] == [0.0, 50.0]
