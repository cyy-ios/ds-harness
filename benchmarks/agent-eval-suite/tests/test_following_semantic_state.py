import json
import sys
from pathlib import Path

RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from evidence_context import ConversationState, write_context_evidence  # noqa: E402
from extract_requirements import extract_requirements_for_round  # noqa: E402
from match_violations import match_violations_for_round  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_conversation_state_captures_discussion_only_plan_and_artifact(tmp_path):
    step = tmp_path / "round_01"
    step.mkdir(parents=True)
    state = ConversationState()
    write_context_evidence(
        step,
        runner="test",
        milestone="M1",
        prompt="只讨论 src/，先别改。采用方案 A。产物格式必须为 JSON。",
        repo_root=tmp_path,
        state=state,
    )
    convo = json.loads((step / "conversation_state.json").read_text(encoding="utf-8"))
    kinds = {c["kind"] for c in convo["active_local_constraints"]}
    assert {"scope", "discussion_only", "chosen_plan", "artifact_contract"} <= kinds


def test_local_discussion_only_becomes_violation_on_edit(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(round_dir / "prompt.json", {"id": "M1", "prompt": "只讨论 src/，先别改。"})
    _write_json(
        round_dir / "conversation_state.json",
        {
            "active_task_chain": {"current_milestone": "M1"},
            "active_local_constraints": [{"kind": "discussion_only", "value": "no_edit_without_new_permission", "source": "M1", "status": "active"}],
            "active_flow_requirements": [],
        },
    )
    req = extract_requirements_for_round(round_dir)
    _write_json(round_dir / "requirements.json", req)
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1",
            "tool_calls": [{"tool": "file_edit", "target": "src/app.py"}],
            "commands": [],
            "edited_files": [{"path": "src/app.py"}],
            "artifacts": [],
            "final_response": "已修改",
            "final_claims": [{"text": "已修改"}],
            "operation_order": [],
        },
    )
    result = match_violations_for_round(round_dir)
    target = [v for v in result["violations"] if v["sub_item"] == "局部持久约束遵循" and v["type"] == "must_not_do"]
    assert target and target[0]["verdict"] == "violated"

