import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from extract_requirements import extract_requirements_for_round  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_extract_requirements_from_prompt_and_context_files(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "prompt.json",
        {
            "round": "round_01",
            "milestone": "M2_config",
            "prompt": "只改 src/。先读取 config.py，再更新 tests。不要 commit，最终只输出 JSON。",
        },
    )
    _write_json(
        round_dir / "active_instructions.json",
        {
            "runner": "deepseek_api",
            "milestone": "M2_config",
            "prompt_ref": "prompt.json",
            "sources": [{"kind": "workspace_rule", "path": "AGENTS.md"}],
        },
    )
    _write_json(
        round_dir / "conversation_state.json",
        {
            "active_task_chain": {"current_milestone": "M2_config", "previous_milestone": "M1_bootstrap"},
            "active_local_constraints": [{"kind": "scope", "value": "src/", "source": "M2_config", "status": "active"}],
            "active_flow_requirements": [
                {"kind": "ordered_steps", "steps": ["读取 config.py", "更新 tests"], "source": "M2_config", "status": "active"}
            ],
            "context_events": [],
            "source_refs": ["prompt.json"],
        },
    )

    result = extract_requirements_for_round(round_dir)

    assert result["milestone"] == "M2_config"
    requirements = result["requirements"]
    assert {r["type"] for r in requirements} >= {"scope_limit", "sequence", "permission", "output_format"}
    assert all(r["scope"] in {"current_turn", "persistent", "local_persistent"} for r in requirements)
    assert all(r["source"] in {"prompt", "active_instructions", "conversation_state"} for r in requirements)
    assert any(r["type"] == "permission" and "commit" in r["text"] for r in requirements)
    assert any(r["type"] == "output_format" and "JSON" in r["text"] for r in requirements)


def test_extract_requirements_records_compact_context_event(tmp_path):
    step_dir = tmp_path / "M8_compact_resume" / "step_01"
    _write_json(
        step_dir / "prompt.json",
        {"id": "M8_compact_resume", "prompt": "上下文已压缩为上方摘要。继续新增 report 模块。"},
    )
    _write_json(
        step_dir / "active_instructions.json",
        {"runner": "codex_cli", "milestone": "M8_compact_resume", "prompt_ref": "prompt.json", "sources": []},
    )
    _write_json(
        step_dir / "conversation_state.json",
        {
            "active_task_chain": {"current_milestone": "M8_compact_resume", "previous_milestone": "M7_memory_report"},
            "active_local_constraints": [],
            "active_flow_requirements": [],
            "context_events": [{"event": "context_compacted", "rebuilt": True}],
            "source_refs": ["prompt.json"],
        },
    )

    result = extract_requirements_for_round(step_dir)

    assert any(r["type"] == "must_do" and "压缩" in r["text"] for r in result["requirements"])


def test_extract_requirements_captures_action_clauses(tmp_path):
    round_dir = tmp_path / "round_02"
    _write_json(
        round_dir / "prompt.json",
        {
            "round": "round_02",
            "prompt": "里程碑 M2_config：增加 JSON/YAML 配置解析；保留早期 CLI run 子命令决策；支持配置缺省和显式路径。",
        },
    )

    result = extract_requirements_for_round(round_dir)

    texts = [r["text"] for r in result["requirements"] if r["type"] == "must_do"]
    assert result["milestone"] == "M2_config"
    assert any("增加 JSON/YAML 配置解析" in text for text in texts)
    assert any("保留早期 CLI run 子命令决策" in text for text in texts)
    assert any("支持配置缺省和显式路径" in text for text in texts)


def test_extract_requirements_handles_nested_labels_and_context_background(tmp_path):
    round_dir = tmp_path / "round_05"
    _write_json(
        round_dir / "prompt.json",
        {
            "round": "round_05",
            "milestone": "M5_context_change",
            "prompt": "里程碑 M5_context_change：现在从 subdir/workbench 继续开发，当前环境含若干项目相关变量；保持主线功能在不同工作目录下可用。",
        },
    )
    result = extract_requirements_for_round(round_dir)
    texts = [r["text"] for r in result["requirements"] if r["type"] == "must_do"]
    assert any("从 subdir/workbench 继续开发" in text for text in texts)
    assert not any("当前环境含若干项目相关变量" in text for text in texts)

    round_dir2 = tmp_path / "round_06"
    _write_json(
        round_dir2 / "prompt.json",
        {
            "round": "round_06",
            "milestone": "M6_interruption",
            "prompt": "里程碑 M6_interruption：中断：解释 logs/unrelated_error.log 和 docs/handoff-note.md；处理完后回到 mini harness 主线继续。",
        },
    )
    result2 = extract_requirements_for_round(round_dir2)
    texts2 = [r["text"] for r in result2["requirements"] if r["type"] == "must_do"]
    assert any("解释 logs/unrelated_error.log 和 docs/handoff-note.md" in text for text in texts2)


if __name__ == "__main__":
    with TemporaryDirectory() as d:
        tmp = Path(d)
        test_extract_requirements_from_prompt_and_context_files(tmp / "case1")
        test_extract_requirements_records_compact_context_event(tmp / "case2")
        test_extract_requirements_captures_action_clauses(tmp / "case3")
        test_extract_requirements_handles_nested_labels_and_context_background(tmp / "case4")
