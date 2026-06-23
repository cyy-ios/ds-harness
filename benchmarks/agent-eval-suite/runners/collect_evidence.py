#!/usr/bin/env python3
"""每轮证据采集器 —— 在 runner 执行过程中旁路落盘 round_N 证据目录。

用法：
  from collect_evidence import EvidenceCollector
  coll = EvidenceCollector(fixture_root, output_root, task_name="mini-data-harness")
  coll.collect_fixtures()
  coll.step_start(milestone_id, step_num, prompt_text)
  coll.step_end(milestone_id, step_num, response_text, tool_call, tool_result)
  coll.finalize()  # 写完最后一轮证据 + index.yaml

产出目录结构：
  evidence/
    index.yaml          # 轮次 → 里程碑 → prompt 索引（人 + agent 可读）
    fixture_files/      # 关键 fixture 文件副本
    round_01/
      prompt.json
      response.md
      replay.jsonl      # 该轮全部 tool call 事件（累积）
      commands.log      # 该轮全部 shell 命令（累积）
      diff.patch
      source_snapshot/
      artifact/
      acceptance.json
      analyzer_output/  # analyze_replay.py 输出
      cost.json
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from evidence_context import ConversationState, write_context_evidence

REQUIRED_ACCEPTANCE_CHECK_KEYS = {
    "package_main_exists", "runner_exports", "public_pytest", "cli_end_to_end",
    "config_json_cli", "cwd_independent_cli", "m4_noise_cli", "acceptance_pytest",
    "memory_aware_report", "unsupported_claims_absent",
}

import yaml


class EvidenceCollector:
    def __init__(
        self,
        fixture_root: str | Path,
        output_root: str | Path,
        task_name: str = "mini-data-harness",
        subject_name: str = "unknown",
        start_round: int = 1,
        runner_name: str = "api_collector",
        instruction_sources: list[dict[str, str]] | None = None,
        tool_policy: dict[str, Any] | None = None,
    ):
        self.root = Path(fixture_root).resolve()
        self.out = Path(output_root).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.task_name = task_name
        self.subject_name = subject_name
        self.runner_name = runner_name
        self.instruction_sources = instruction_sources
        self.tool_policy = tool_policy or {"collector": "EvidenceCollector"}
        self.timestamp = time.strftime("%Y%m%d%H%M")

        # 轮次状态
        self._round_num = start_round - 1
        self._current_round: str | None = None
        self._current_milestone: str | None = None
        self._round_dir: Path | None = None
        self._replay_events: list[dict] = []
        self._commands: list[dict] = []
        self._tokens_in = 0
        self._tokens_out = 0
        self._round_start_time: float = 0.0
        self._index_entries: list[dict] = []
        self._conversation_state = ConversationState()
        self._pending_context_events: list[dict[str, Any]] = []
        self._restore_conversation_state(start_round)

    # ------------------------------------------------------------------
    # public API（与旧版兼容）
    # ------------------------------------------------------------------

    def set_context_events(self, events: list[dict[str, Any]]) -> None:
        self._pending_context_events = list(events)

    def _restore_conversation_state(self, start_round: int) -> None:
        if start_round <= 1:
            return
        prev = self.out / f"round_{start_round - 1:02d}" / "conversation_state.json"
        if not prev.exists():
            return
        try:
            data = json.loads(prev.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        chain = data.get("active_task_chain") or {}
        self._conversation_state.last_milestone = chain.get("current_milestone")
        self._conversation_state.previous_milestone = chain.get("previous_milestone")
        self._conversation_state.active_local_constraints = list(data.get("active_local_constraints") or [])
        self._conversation_state.active_flow_requirements = list(data.get("active_flow_requirements") or [])

    def collect_fixtures(self) -> None:
        """采集关键 fixture 文件到 evidence/fixture_files/。"""
        dest = self.out / "fixture_files"
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir()

        for src_rel in [
            "skills",
            "docs",
            "memory",
            "benchmarks",
            "AGENTS.md",
            "CLAUDE.md",
            "README.md",
        ]:
            src = self.root / src_rel
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(
                    src, dest / src_rel,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".git"),
                )
            else:
                shutil.copy2(src, dest / src_rel)

    def step_start(self, milestone_id: str, step_num: int, prompt_text: str) -> str:
        """新 tool step 开始。step_num==0 时开启新一轮。返回当前 round key。"""
        if step_num == 0:
            self._finalize_current_round()
            self._round_num += 1
            self._current_round = f"round_{self._round_num:02d}"
            self._current_milestone = milestone_id
            self._round_dir = self.out / self._current_round
            self._round_dir.mkdir(parents=True, exist_ok=True)
            self._replay_events = []
            self._commands = []
            self._tokens_in = 0
            self._tokens_out = 0
            self._round_start_time = time.monotonic()
            self._index_entries.append({
                "round": self._current_round,
                "milestone": milestone_id,
                "prompt": prompt_text,
            })
            self._save_prompt(prompt_text)
            write_context_evidence(
                self._round_dir,
                runner=self.runner_name,
                milestone=milestone_id,
                prompt=prompt_text,
                repo_root=self.root,
                state=self._conversation_state,
                instruction_sources=self.instruction_sources,
                tool_policy=self.tool_policy,
                context_events=self._pending_context_events,
            )
            self._pending_context_events = []
            self._snapshot_pre()
        return self._current_round or ""

    def step_end(
        self,
        milestone_id: str,
        step_num: int,
        response_text: str,
        tool_call: dict | None = None,
        tool_result: dict | None = None,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """记录一个 tool step 结束，证据累积到当前轮目录。"""
        if not self._round_dir:
            return

        self._tokens_in += input_tokens
        self._tokens_out += output_tokens

        # response：只保留 finish 的 summary 文本，跳过中间 tool_call JSON
        if tool_call and tool_call.get("tool") == "finish":
            summary = tool_call.get("summary", response_text)
            self._save_response(summary)
        # replay：累积
        if tool_call:
            self._replay_events.append({"role": "assistant", "tool_call": tool_call})
        if tool_result:
            self._replay_events.append({"role": "tool", "result": tool_result})
        # commands：累积
        if tool_call and tool_call.get("tool") == "shell":
            self._commands.append({
                "command": tool_call.get("cmd", ""),
                "cwd": str(self.root),
                "exit_code": tool_result.get("returncode") if tool_result else None,
                "stdout": (tool_result.get("output", "") or "")[:20000] if tool_result else "",
            })

        # finish 时封存本轮
        if tool_call and tool_call.get("tool") == "finish":
            self._finalize_current_round()
            self._current_round = None
            self._current_milestone = None
            self._round_dir = None

    def finalize(self) -> None:
        """全部轮次结束后调用：封存最后一轮 + 写 index.yaml。"""
        self._finalize_current_round()
        self._write_index()

    # ------------------------------------------------------------------
    # 轮次封存
    # ------------------------------------------------------------------

    def _finalize_current_round(self) -> None:
        if not self._round_dir:
            return
        self._write_replay()
        self._write_commands()
        self._save_diff()
        self._save_file_tree()
        self._save_source_snapshot()
        self._save_artifact()
        self._run_acceptance()
        self._run_analyzer()
        self._save_cost()

    # ------------------------------------------------------------------
    # per-file savers
    # ------------------------------------------------------------------

    def _save_prompt(self, text: str) -> None:
        (self._round_dir / "prompt.json").write_text(
            json.dumps({"round": self._current_round, "milestone": self._current_milestone, "prompt": text}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_response(self, text: str) -> None:
        (self._round_dir / "response.md").write_text(text, encoding="utf-8")

    def _write_replay(self) -> None:
        content = "\n".join(json.dumps(e, ensure_ascii=False) for e in self._replay_events) + "\n"
        (self._round_dir / "replay.jsonl").write_text(content, encoding="utf-8")

    def _write_commands(self) -> None:
        (self._round_dir / "commands.log").write_text(
            json.dumps(self._commands, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _save_diff(self) -> None:
        try:
            # git add -A 将新文件也纳入 diff 范围
            subprocess.run(
                ["git", "-C", str(self.root), "add", "-A"],
                capture_output=True, timeout=10,
            )
            diff = subprocess.run(
                ["git", "-C", str(self.root), "diff", "--cached", "HEAD", "--no-color"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            )
            patch = diff.stdout
        except Exception:
            patch = ""
        (self._round_dir / "diff.patch").write_text(patch or "(no changes)", encoding="utf-8")

    def _save_file_tree(self) -> None:
        try:
            tree = subprocess.run(
                ["find", str(self.root), "-not", "-path", "*/.git/*",
                 "-not", "-path", "*/__pycache__/*", "-not", "-path", "*.pyc",
                 "-not", "-path", "*/.pytest_cache/*"],
                capture_output=True, text=True, timeout=10,
            )
            text = tree.stdout
        except Exception:
            text = ""
        (self._round_dir / "file_tree.txt").write_text(text, encoding="utf-8")

    def _save_source_snapshot(self) -> None:
        snap = self._round_dir / "source_snapshot"
        if snap.exists():
            shutil.rmtree(snap)
        snap.mkdir()
        for sub in ["src", "tests", "skills"]:
            src = self.root / sub
            if src.is_dir():
                shutil.copytree(
                    src, snap / sub,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
                )

    def _save_artifact(self) -> None:
        art = self._round_dir / "artifact"
        if art.exists():
            shutil.rmtree(art)
        art.mkdir()
        for pattern in ["*.json", "*.md", "*.txt", "*.log"]:
            for f in self.root.glob(pattern):
                if f.name.startswith("."):
                    continue
                dest = art / f.name
                if not dest.exists():
                    shutil.copy2(f, dest)
        tmp_dir = self.root / "tmp"
        if tmp_dir.is_dir():
            dest_tmp = art / "tmp"
            dest_tmp.mkdir(exist_ok=True)
            for f in tmp_dir.rglob("*"):
                if f.is_file() and "__pycache__" not in str(f):
                    rel = f.relative_to(tmp_dir)
                    (dest_tmp / rel.parent).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest_tmp / rel)

    def _run_acceptance(self) -> None:
        result = {"ran": False, "error": "acceptance scorer not found"}
        scorer = Path(__file__).resolve().parent / "score_mini_data_harness.py"
        if scorer.exists():
            try:
                cmd = ["python", str(scorer), str(self.root)]
                if self._current_round:
                    cmd += ["--round", self._current_round]
                if self._current_milestone:
                    cmd += ["--milestone", self._current_milestone]
                cp = subprocess.run(
                    cmd,
                    capture_output=True, text=True, timeout=120,
                )
                result = {
                    "ran": True,
                    "returncode": cp.returncode,
                    "cmd": cmd,
                    "output": cp.stdout,
                    "stderr": cp.stderr,
                }
                try:
                    parsed = json.loads(cp.stdout)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    checks = parsed.get("checks", {})
                    missing = sorted(REQUIRED_ACCEPTANCE_CHECK_KEYS - set(checks)) if isinstance(checks, dict) else sorted(REQUIRED_ACCEPTANCE_CHECK_KEYS)
                    if missing:
                        result["schema_error"] = f"missing acceptance checks: {missing}"
                        result["missing_check_keys"] = missing
                    result["parsed"] = parsed
                    for key in [
                        "score",
                        "max_score",
                        "round",
                        "milestone",
                        "stage",
                        "gate_scope",
                        "gate_passed",
                        "final_gate_applicable",
                        "final_gate_passed",
                    ]:
                        if key in parsed:
                            result[key] = parsed[key]
            except Exception as e:
                result = {"ran": False, "error": str(e)}
        (self._round_dir / "acceptance.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _run_analyzer(self) -> None:
        """运行 analyze_replay.py，输出到 analyzer_output/。"""
        out_dir = self._round_dir / "analyzer_output"
        out_dir.mkdir(exist_ok=True)
        analyzer = Path(__file__).resolve().parent / "analyze_replay.py"
        if not analyzer.exists():
            (out_dir / "analyzer.json").write_text(
                json.dumps({"ran": False, "error": "analyze_replay.py not found"}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return

        replay_path = self._round_dir / "replay.jsonl"
        response_path = self._round_dir / "response.md"
        paths = []
        if replay_path.exists():
            paths.append(str(replay_path))
        if response_path.exists():
            paths.append(str(response_path))

        if not paths:
            (out_dir / "analyzer.json").write_text(
                json.dumps({"ran": False, "error": "no replay or response to analyze"}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return

        try:
            cp = subprocess.run(
                ["python", str(analyzer)] + paths,
                capture_output=True, text=True, timeout=30,
            )
            (out_dir / "analyzer.json").write_text(
                cp.stdout if cp.returncode == 0
                else json.dumps({"ran": False, "returncode": cp.returncode, "stderr": cp.stderr[:2000]}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            (out_dir / "analyzer.json").write_text(
                json.dumps({"ran": False, "error": str(e)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _save_cost(self) -> None:
        elapsed = time.monotonic() - self._round_start_time
        (self._round_dir / "cost.json").write_text(
            json.dumps({
                "elapsed_sec": round(elapsed, 2),
                "input_tokens": self._tokens_in,
                "output_tokens": self._tokens_out,
                "total_tokens": self._tokens_in + self._tokens_out,
                "tool_steps": len([e for e in self._replay_events if e.get("role") == "assistant"]),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # index.yaml
    # ------------------------------------------------------------------

    def _write_index(self) -> None:
        index_path = self.out / "index.yaml"
        data = {
            "subject": self.subject_name,
            "task": self.task_name,
            "timestamp": self.timestamp,
            "total_rounds": len(self._index_entries),
            "rounds": self._index_entries,
        }
        index_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _snapshot_pre(self) -> None:
        """git add -A && commit，使得本轮 diff 相对于本轮开始时状态。"""
        git_dir = self.root / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "-C", str(self.root), "init"], capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(self.root), "config", "user.email", "harness@eval"], capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(self.root), "config", "user.name", "harness"], capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], capture_output=True, timeout=10)
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "--allow-empty", "-m", f"snapshot:{self._current_round}"],
            capture_output=True, timeout=10,
        )
