import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from evidence_context import write_context_evidence  # noqa: E402


def test_write_context_evidence_uses_references_not_prompt_copies(tmp_path):
    step_dir = tmp_path / "M2_config" / "step_01"
    step_dir.mkdir(parents=True)


    write_context_evidence(
        step_dir,
        runner="codex_cli",
        milestone="M2_config",
        prompt="Keep changes under src/ only. First inspect config.py, then update tests.",
        repo_root=tmp_path,
        instruction_sources=[{"kind": "runner_config", "path": ".codex/instructions.md"}],
        tool_policy={"allowed_tools": ["shell", "file_edit"], "approval_policy": "never"},
    )

    active = json.loads((step_dir / "active_instructions.json").read_text(encoding="utf-8"))
    policy = json.loads((step_dir / "tool_policy_events.json").read_text(encoding="utf-8"))

    assert active["milestone"] == "M2_config"
    assert active["sources"] == [{"kind": "runner_config", "path": ".codex/instructions.md"}]
    assert active["prompt_ref"] == "prompt.json"
    assert "Keep changes under src" not in json.dumps(active, ensure_ascii=False)

    assert policy["runner"] == "codex_cli"
    assert policy["policy"]["allowed_tools"] == ["shell", "file_edit"]
    assert policy["events"] == []


if __name__ == "__main__":
    with TemporaryDirectory() as d:
        test_write_context_evidence_uses_references_not_prompt_copies(Path(d))
