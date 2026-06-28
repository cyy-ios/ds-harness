#!/usr/bin/env python3
"""Collect the new per-round evidence contract: tool events plus result."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from response_protocol import write_result_json
from tool_events import from_tool_pairs, write_jsonl


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
        self._final_response = ""
        self._tokens_in = 0
        self._tokens_out = 0
        self._round_start_time: float = 0.0
        self._index_entries: list[dict] = []
        self._pending_context_events: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # public API（与旧版兼容）
    # ------------------------------------------------------------------

    def set_context_events(self, events: list[dict[str, Any]]) -> None:
        self._pending_context_events = list(events)

    def collect_fixtures(self) -> None:
        """No-op: fixture snapshots are no longer evidence."""
        return

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
            self._final_response = ""
            self._tokens_in = 0
            self._tokens_out = 0
            self._round_start_time = time.monotonic()
            self._index_entries.append({
                "round": self._current_round,
                "milestone": milestone_id,
                "prompt": prompt_text,
            })
            self._pending_context_events = []
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

        # replay：累积
        if tool_call:
            self._replay_events.append({"role": "assistant", "tool_call": tool_call})
        if tool_result:
            self._replay_events.append({"role": "tool", "result": tool_result})
        # finish 时封存本轮
        if tool_call and tool_call.get("tool") == "finish":
            self._final_response = str(tool_call.get("summary") or response_text or "")
            self._finalize_current_round()
            self._current_round = None
            self._current_milestone = None
            self._round_dir = None

    def finalize(self) -> None:
        """全部轮次结束后调用：封存最后一轮 + 写 index.json。"""
        self._finalize_current_round()
        self._write_index()

    # ------------------------------------------------------------------
    # 轮次封存
    # ------------------------------------------------------------------

    def _finalize_current_round(self) -> None:
        if not self._round_dir:
            return
        self._write_tool_events()
        self._write_result()

    def _write_tool_events(self) -> None:
        pairs: list[tuple[dict[str, Any] | None, dict[str, Any] | None]] = []
        pending: dict[str, Any] | None = None
        for event in self._replay_events:
            if event.get("role") == "assistant":
                pending = event.get("tool_call")
            elif event.get("role") == "tool":
                pairs.append((pending, event.get("result")))
                pending = None
        if pending is not None:
            pairs.append((pending, None))
        write_jsonl(
            self._round_dir / "tool_events.jsonl",
            from_tool_pairs(pairs, self._current_milestone or ""),
        )


    def _write_result(self) -> None:
        write_result_json(
            self._round_dir / "result.json",
            milestone=self._current_milestone or "",
            runner=self.runner_name,
            final_response=self._final_response,
            elapsed_seconds=round(time.monotonic() - self._round_start_time, 3) if self._round_start_time else None,
            extra={
                "task_name": self.task_name,
                "subject_name": self.subject_name,
                "tokens": {"input": self._tokens_in, "output": self._tokens_out},
            },
        )

    def _write_index(self) -> None:
        (self.out / "index.json").write_text(
            json.dumps(
                {
                    "task_name": self.task_name,
                    "subject_name": self.subject_name,
                    "runner": self.runner_name,
                    "evidence_contract": "tool_events_result_v1",
                    "rounds": self._index_entries,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

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
