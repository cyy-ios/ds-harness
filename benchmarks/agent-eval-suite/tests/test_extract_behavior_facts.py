import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from extract_behavior_facts import extract_behavior_facts_for_round  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_extract_behavior_facts_from_api_replay_commands_diff_and_response(tmp_path):
    round_dir = tmp_path / "round_06"
    _write(
        round_dir / "replay.jsonl",
        "\n".join(
            [
                json.dumps({"role": "assistant", "tool_call": {"tool": "read_file", "path": "logs/unrelated_error.log"}}),
                json.dumps({"role": "tool", "result": {"ok": True, "content": "ERROR external cache timeout"}}),
                json.dumps({"role": "assistant", "tool_call": {"tool": "write_file", "path": "docs/report.md", "content": "done"}}),
                json.dumps({"role": "tool", "result": {"ok": True, "path": "docs/report.md"}}),
                json.dumps({"role": "assistant", "tool_call": {"tool": "finish", "summary": "已读取日志并完成报告。", "tests": "pytest -q"}}),
            ]
        ),
    )
    _write(
        round_dir / "commands.log",
        json.dumps(
            [
                {
                    "command": "PYTHONDONTWRITEBYTECODE=1 python -m pytest -q",
                    "cwd": "/tmp/fixture",
                    "exit_code": 0,
                    "stdout": "1 passed",
                }
            ],
            ensure_ascii=False,
        ),
    )
    _write(
        round_dir / "diff.patch",
        "diff --git a/docs/report.md b/docs/report.md\nnew file mode 100644\n--- /dev/null\n+++ b/docs/report.md\n@@ -0,0 +1 @@\n+done\n",
    )
    _write(round_dir / "response.md", "已读取日志并完成报告。\n测试通过。")
    _write(round_dir / "artifact" / "docs" / "report.md", "done")

    result = extract_behavior_facts_for_round(round_dir)

    assert result["round_dir"] == "round_06"
    assert any(call["tool"] == "read_file" and call["target"] == "logs/unrelated_error.log" for call in result["tool_calls"])
    assert any(call["tool"] == "write_file" and call.get("content_excerpt") == "done" for call in result["tool_calls"])
    assert any(cmd["exit_code"] == 0 and "pytest" in cmd["command"] for cmd in result["commands"])
    assert any(f["path"] == "docs/report.md" and f["change_type"] == "added" for f in result["edited_files"])
    assert any(a["path"] == "docs/report.md" for a in result["artifacts"])
    assert any("测试通过" in c["text"] for c in result["final_claims"])
    assert result["operation_order"][0]["kind"] == "tool_call"


def test_extract_behavior_facts_from_codex_style_replay_without_commands_log(tmp_path):
    step_dir = tmp_path / "M6_interruption" / "step_01"
    _write(
        step_dir / "replay.jsonl",
        "\n".join(
            [
                json.dumps(
                    {
                        "milestone": "M6_interruption",
                        "step": 0,
                        "tool": "command_execution",
                        "tool_input": {"command": "Get-Content logs/unrelated_error.log"},
                        "event_type": "tool_call",
                    }
                ),
                json.dumps(
                    {
                        "milestone": "M6_interruption",
                        "step": 1,
                        "tool": "command_execution",
                        "tool_output": "ERROR external cache timeout",
                        "tool_error": False,
                        "event_type": "tool_result",
                    }
                ),
                json.dumps(
                    {
                        "milestone": "M6_interruption",
                        "step": 2,
                        "assistant_text": "日志与 mini harness 无关。",
                        "event_type": "agent_message",
                    }
                ),
            ]
        ),
    )
    _write(step_dir / "diff.patch", "(no changes)")
    _write(step_dir / "response.md", "日志与 mini harness 无关。")

    result = extract_behavior_facts_for_round(step_dir)

    assert any(call["tool"] == "command_execution" for call in result["tool_calls"])
    assert any("Get-Content logs/unrelated_error.log" in cmd["command"] for cmd in result["commands"])
    assert result["edited_files"] == []
    assert any("mini harness 无关" in claim["text"] for claim in result["final_claims"])


def test_extract_behavior_facts_reads_claude_file_path_target(tmp_path):
    step_dir = tmp_path / "M1_bootstrap" / "step_01"
    _write(
        step_dir / "replay.jsonl",
        json.dumps(
            {
                "milestone": "M1_bootstrap",
                "step": 0,
                "tool": "Read",
                "tool_input": {"file_path": r"C:\repo\skills\data-harness\SKILL.md"},
                "event_type": "tool_call",
            }
        ),
    )

    result = extract_behavior_facts_for_round(step_dir)

    assert result["tool_calls"][0]["target"] == r"C:\repo\skills\data-harness\SKILL.md"


def test_extract_behavior_facts_preserves_repeated_replay_commands(tmp_path):
    step_dir = tmp_path / "M2_config" / "step_01"
    _write(
        step_dir / "replay.jsonl",
        "\n".join(
            [
                json.dumps({"tool": "command_execution", "tool_input": {"command": "pytest -q"}, "event_type": "tool_call", "event_id": "a"}),
                json.dumps({"tool": "command_execution", "tool_input": {"command": "pytest -q"}, "event_type": "tool_call", "event_id": "b"}),
            ]
        ),
    )

    result = extract_behavior_facts_for_round(step_dir)

    assert [cmd["command"] for cmd in result["commands"]] == ["pytest -q", "pytest -q"]


if __name__ == "__main__":
    with TemporaryDirectory() as d:
        tmp = Path(d)
        test_extract_behavior_facts_from_api_replay_commands_diff_and_response(tmp / "case1")
        test_extract_behavior_facts_from_codex_style_replay_without_commands_log(tmp / "case2")
        test_extract_behavior_facts_reads_claude_file_path_target(tmp / "case3")
        test_extract_behavior_facts_preserves_repeated_replay_commands(tmp / "case4")
