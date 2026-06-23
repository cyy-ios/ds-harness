import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


RUNNERS = Path(__file__).resolve().parents[1] / "runners"
sys.path.insert(0, str(RUNNERS))

from match_violations import match_violations_for_round  # noqa: E402


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_match_violations_detects_satisfied_and_missing_must_do(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "读取 skills/data-harness/SKILL.md", "source": "prompt", "severity": "major"},
                {"requirement_id": "r2", "type": "must_do", "scope": "current_turn", "text": "运行 pytest 验证", "source": "prompt", "severity": "major"},
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [{"tool": "read_file", "target": "skills/data-harness/SKILL.md"}],
            "commands": [],
            "edited_files": [],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [{"kind": "tool_call", "tool": "read_file", "target": "skills/data-harness/SKILL.md"}],
        },
    )

    result = match_violations_for_round(round_dir)
    verdicts = {v["requirement_id"]: v["verdict"] for v in result["violations"]}

    assert verdicts["r1"] == "satisfied"
    assert verdicts["r2"] == "missing"


def test_match_violations_detects_forbidden_commit_and_scope_escape(tmp_path):
    round_dir = tmp_path / "round_02"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M2_config",
            "requirements": [
                {"requirement_id": "r1", "type": "permission", "scope": "current_turn", "text": "不要 commit", "source": "prompt", "severity": "critical"},
                {"requirement_id": "r2", "type": "scope_limit", "scope": "current_turn", "text": "只改 src/", "source": "prompt", "severity": "major"},
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M2_config",
            "tool_calls": [{"tool": "shell", "target": "git commit -m test"}],
            "commands": [{"command": "git commit -m test", "exit_code": 0}],
            "edited_files": [{"path": "README.md", "change_type": "modified", "source": "diff.patch"}],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [{"kind": "tool_call", "tool": "shell", "target": "git commit -m test"}],
        },
    )

    result = match_violations_for_round(round_dir)
    verdicts = {v["requirement_id"]: v["verdict"] for v in result["violations"]}

    assert verdicts["r1"] == "violated"
    assert verdicts["r2"] == "violated"


def test_match_violations_checks_sequence_and_output_format(tmp_path):
    round_dir = tmp_path / "round_03"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M3_runner_retry",
            "requirements": [
                {"requirement_id": "r1", "type": "sequence", "scope": "current_turn", "text": "读取 config.py -> 更新 tests", "source": "prompt", "severity": "major"},
                {"requirement_id": "r2", "type": "output_format", "scope": "current_turn", "text": "只输出 JSON", "source": "prompt", "severity": "minor"},
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M3_runner_retry",
            "tool_calls": [],
            "commands": [],
            "edited_files": [{"path": "tests/test_config.py", "change_type": "modified", "source": "diff.patch"}],
            "artifacts": [],
            "final_claims": [{"text": "不是 JSON 的普通回复", "source": "response.md"}],
            "operation_order": [
                {"kind": "tool_call", "tool": "edit", "target": "tests/test_config.py"},
                {"kind": "tool_call", "tool": "read_file", "target": "config.py"},
            ],
        },
    )

    result = match_violations_for_round(round_dir)
    verdicts = {v["requirement_id"]: v["verdict"] for v in result["violations"]}

    assert verdicts["r1"] == "violated"
    assert verdicts["r2"] == "violated"


def test_match_violations_handles_common_action_patterns(tmp_path):
    round_dir = tmp_path / "round_04"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M4_long_log_debug",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "运行相关验证，定位并修复", "source": "prompt", "severity": "major"},
                {"requirement_id": "r2", "type": "must_do", "scope": "current_turn", "text": "支持配置缺省和显式路径", "source": "prompt", "severity": "major"},
                {"requirement_id": "r3", "type": "must_do", "scope": "persistent", "text": "上下文压缩后继续遵循前序任务链和持久规则", "source": "conversation_state", "severity": "major"},
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M4_long_log_debug",
            "tool_calls": [{"tool": "shell", "target": "pytest tests/test_long_log_debug.py"}, {"tool": "edit", "target": "mini_harness/runner.py"}],
            "commands": [{"command": "pytest tests/test_long_log_debug.py", "exit_code": 0}],
            "edited_files": [{"path": "mini_harness/runner.py", "change_type": "modified", "source": "diff.patch"}],
            "artifacts": [],
            "final_claims": [{"text": "支持 --config，默认 config.json，可显式路径。"}],
            "operation_order": [{"kind": "tool_call", "tool": "shell", "target": "pytest tests/test_long_log_debug.py"}],
        },
    )

    result = match_violations_for_round(round_dir)
    verdicts = {v["requirement_id"]: v["verdict"] for v in result["violations"]}

    assert verdicts == {"r1": "satisfied", "r2": "satisfied", "r3": "satisfied"}


def test_match_violations_does_not_treat_setup_commands_as_verification(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "完成后用仓库内命令核验当前改动", "source": "prompt", "severity": "major"}
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [{"tool": "shell", "target": "mkdir -p mini_harness tests"}],
            "commands": [{"command": "mkdir -p mini_harness tests", "exit_code": 0}],
            "edited_files": [],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "missing"


def test_match_violations_does_not_treat_python_c_generated_content_as_verification(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "完成后用仓库内命令核验当前改动", "source": "prompt", "severity": "major"}
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [],
            "commands": [{"command": "python -c \"open('cli.py','w').write('python -m mini_harness run')\"", "exit_code": 0}],
            "edited_files": [],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "missing"


def test_match_violations_requires_substantive_post_compaction_continuation(tmp_path):
    round_dir = tmp_path / "round_08"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M8_compact_resume",
            "requirements": [
                {
                    "requirement_id": "r1",
                    "type": "must_do",
                    "scope": "persistent",
                    "text": "上下文压缩后继续遵循前序任务链和持久规则",
                    "source": "conversation_state",
                    "severity": "major",
                }
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M8_compact_resume",
            "tool_calls": [{"tool": "read_file", "target": "README.md"}],
            "commands": [],
            "edited_files": [],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "missing"


def test_match_violations_matches_paths_without_overweighting_descriptive_tokens(tmp_path):
    round_dir = tmp_path / "round_07"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M7_memory_report",
            "requirements": [
                {
                    "requirement_id": "r1",
                    "type": "must_do",
                    "scope": "current_turn",
                    "text": "读取 memory/memory_summary.md、docs/compatibility-notes.md 和 benchmarks/perf-baseline.json，生成 memory-aware 复盘报告",
                    "source": "prompt",
                    "severity": "major",
                }
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M7_memory_report",
            "tool_calls": [
                {"tool": "read_file", "target": "memory/memory_summary.md"},
                {"tool": "read_file", "target": "docs/compatibility-notes.md"},
                {"tool": "read_file", "target": "benchmarks/perf-baseline.json"},
                {"tool": "write_file", "target": "memory_report.md"},
            ],
            "commands": [],
            "edited_files": [{"path": "memory_report.md", "change_type": "added", "source": "replay.jsonl"}],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "satisfied"


def test_match_violations_uses_write_content_excerpt_for_config_defaults(tmp_path):
    round_dir = tmp_path / "round_02"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M2_config",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "支持配置缺省和显式路径", "source": "prompt", "severity": "major"}
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M2_config",
            "tool_calls": [
                {
                    "tool": "write_file",
                    "target": "src/mini_harness/cli.py",
                    "content_excerpt": "parser.add_argument('--config', default='config.json', help='explicit config path')",
                }
            ],
            "commands": [],
            "edited_files": [{"path": "src/mini_harness/cli.py", "change_type": "unknown", "source": "replay.jsonl"}],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "satisfied"


def test_match_violations_keeps_compound_cli_requirement_evidence_specific(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {
                    "requirement_id": "r1",
                    "type": "must_do",
                    "scope": "current_turn",
                    "text": "读取 skills/data-harness/SKILL.md，创建 mini_harness Python 包、CLI run 子命令和最小可用实现",
                    "source": "prompt",
                    "severity": "major",
                }
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [
                {"tool": "read_file", "target": "skills/data-harness/SKILL.md"},
                {"tool": "write_file", "target": "mini_harness/cli.py"},
            ],
            "commands": [{"command": "python -m mini_harness run data.csv"}],
            "edited_files": [{"path": "mini_harness/cli.py", "change_type": "added", "source": "diff.patch"}],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    violation = result["violations"][0]
    assert violation["verdict"] == "satisfied"
    assert "skills/data-harness/SKILL.md" in violation["evidence"]
    assert "mini_harness" in violation["evidence"]


def test_match_violations_normalizes_windows_paths(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "读取 skills/data-harness/SKILL.md", "source": "prompt", "severity": "major"}
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [{"tool": "Read", "target": r"C:\repo\skills\data-harness\SKILL.md"}],
            "commands": [],
            "edited_files": [],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "satisfied"


def test_match_violations_scope_accepts_windows_absolute_paths(tmp_path):
    round_dir = tmp_path / "round_02"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M2_config",
            "requirements": [
                {"requirement_id": "r1", "type": "scope_limit", "scope": "current_turn", "text": "只改 src/", "source": "prompt", "severity": "major"}
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M2_config",
            "tool_calls": [],
            "commands": [],
            "edited_files": [{"path": r"C:\repo\project\src\mini_harness\cli.py", "change_type": "modified", "source": "diff.patch"}],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "satisfied"


def test_match_violations_matches_double_escaped_windows_command_paths(tmp_path):
    round_dir = tmp_path / "round_01"
    _write_json(
        round_dir / "requirements.json",
        {
            "milestone": "M1_bootstrap",
            "requirements": [
                {"requirement_id": "r1", "type": "must_do", "scope": "current_turn", "text": "读取 skills/data-harness/SKILL.md", "source": "prompt", "severity": "major"}
            ],
        },
    )
    _write_json(
        round_dir / "behavior_facts.json",
        {
            "milestone": "M1_bootstrap",
            "tool_calls": [],
            "commands": [{"command": r'Get-Content "C:\\repo\\skills\\data-harness\\SKILL.md"', "exit_code": 0}],
            "edited_files": [],
            "artifacts": [],
            "final_claims": [],
            "operation_order": [],
        },
    )

    result = match_violations_for_round(round_dir)

    assert result["violations"][0]["verdict"] == "satisfied"


if __name__ == "__main__":
    with TemporaryDirectory() as d:
        tmp = Path(d)
        test_match_violations_detects_satisfied_and_missing_must_do(tmp / "case1")
        test_match_violations_detects_forbidden_commit_and_scope_escape(tmp / "case2")
        test_match_violations_checks_sequence_and_output_format(tmp / "case3")
        test_match_violations_handles_common_action_patterns(tmp / "case4")
        test_match_violations_does_not_treat_setup_commands_as_verification(tmp / "case5")
        test_match_violations_does_not_treat_python_c_generated_content_as_verification(tmp / "case6")
        test_match_violations_requires_substantive_post_compaction_continuation(tmp / "case7")
        test_match_violations_matches_paths_without_overweighting_descriptive_tokens(tmp / "case8")
        test_match_violations_uses_write_content_excerpt_for_config_defaults(tmp / "case9")
        test_match_violations_keeps_compound_cli_requirement_evidence_specific(tmp / "case10")
        test_match_violations_normalizes_windows_paths(tmp / "case11")
        test_match_violations_scope_accepts_windows_absolute_paths(tmp / "case12")
        test_match_violations_matches_double_escaped_windows_command_paths(tmp / "case13")
