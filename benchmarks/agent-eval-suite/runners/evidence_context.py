#!/usr/bin/env python3
"""Lightweight context evidence for following scoring."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCOPE_RE = re.compile(r"(?:under|within|inside|only in|只(?:能|在|改|处理|讨论)|范围(?:是|为|:|：)|鍙.{0,6}鏀)\s*`?([\w./\\-]+)`?", re.I)
_FLOW_RE = re.compile(r"(?:first|先)\s*(.+?)(?:,\s*then|，再|再|then)\s*(.+?)(?:[.。；;\n]|$)", re.I)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("`'\" "))


def _has_text(items: list[dict[str, Any]], kind: str, value: str) -> bool:
    return any(i.get("kind") == kind and i.get("value") == value and i.get("status", "active") == "active" for i in items)


@dataclass
class ConversationState:
    active_local_constraints: list[dict[str, Any]] = field(default_factory=list)
    active_flow_requirements: list[dict[str, Any]] = field(default_factory=list)
    last_milestone: str | None = None
    previous_milestone: str | None = None

    def update_from_prompt(self, *, milestone: str, prompt: str) -> None:
        self.previous_milestone = self.last_milestone
        self.last_milestone = milestone
        lower = prompt.lower()
        if any(word in lower for word in ("撤销", "取消", "reset", "ignore previous", "鎾ら攢", "鍙栨秷")):
            self.active_local_constraints.clear()
            self.active_flow_requirements.clear()

        # Topic switch normally ends local constraints but preserves persistent flow unless explicitly reset.
        if re.search(r"(切换|换个|新任务|另一个问题|different task|new topic)", prompt, re.I):
            self.active_local_constraints.clear()

        for match in _SCOPE_RE.finditer(prompt):
            value = _clean(match.group(1))
            self._add_constraint(milestone, "scope", value)

        if re.search(r"(只讨论|先别改|不要改|别改|只解释|只分析|discussion only|no edit)", prompt, re.I):
            self._add_constraint(milestone, "discussion_only", "no_edit_without_new_permission")

        plan = re.search(r"(?:采用|确定|按|使用|选择)\s*([A-Za-z0-9_\- ]{1,40}|方案\s*[A-Za-z0-9_\-]+)", prompt)
        if plan:
            self._add_constraint(milestone, "chosen_plan", _clean(plan.group(1)))

        if re.search(r"(纠正|更正|不是补充|覆盖之前|以这次为准|correction|override)", prompt, re.I):
            self._add_constraint(milestone, "correction_overrides_old_fact", _clean(prompt[:240]))

        if re.search(r"(支线|临时排查|旁支|side branch|temporary investigation)", prompt, re.I):
            self._add_constraint(milestone, "side_branch", _clean(prompt[:200]))

        artifact = re.search(r"(?:产物|artifact|输出文件|报告|格式)\s*(?:必须|要|为|是|:)\s*([^。；;\n]{2,120})", prompt, re.I)
        if artifact:
            self._add_constraint(milestone, "artifact_contract", _clean(artifact.group(1)))

        flow = _FLOW_RE.search(prompt)
        if flow:
            self._add_flow(milestone, [_clean(flow.group(1)), _clean(flow.group(2))])
        if re.search(r"(按流程|流程|checklist|逐项|每步|阶段)", prompt, re.I):
            self._add_flow(milestone, [_clean(prompt[:160])])

    def _add_constraint(self, milestone: str, kind: str, value: str) -> None:
        if value and not _has_text(self.active_local_constraints, kind, value):
            self.active_local_constraints.append({"kind": kind, "value": value, "source": milestone, "status": "active"})

    def _add_flow(self, milestone: str, steps: list[str]) -> None:
        steps = [s for s in steps if s]
        if not steps:
            return
        key = " -> ".join(steps)
        if not any(" -> ".join(f.get("steps") or []) == key and f.get("status", "active") == "active" for f in self.active_flow_requirements):
            self.active_flow_requirements.append({"kind": "ordered_steps", "steps": steps, "source": milestone, "status": "active", "current_entry": steps[0]})

    def to_json(self, *, milestone: str) -> dict[str, Any]:
        return {
            "active_task_chain": {"current_milestone": milestone, "previous_milestone": self.previous_milestone},
            "active_local_constraints": self.active_local_constraints,
            "active_flow_requirements": self.active_flow_requirements,
            "source_refs": ["prompt.json"],
        }


def write_context_evidence(
    step_dir: Path,
    *,
    runner: str,
    milestone: str,
    prompt: str,
    repo_root: Path,
    state: ConversationState,
    instruction_sources: list[dict[str, str]] | None = None,
    tool_policy: dict[str, Any] | None = None,
    tool_policy_events: list[dict[str, Any]] | None = None,
    context_events: list[dict[str, Any]] | None = None,
) -> None:
    state.update_from_prompt(milestone=milestone, prompt=prompt)
    sources = instruction_sources if instruction_sources is not None else discover_instruction_sources(repo_root)
    (step_dir / "active_instructions.json").write_text(json.dumps({"runner": runner, "milestone": milestone, "prompt_ref": "prompt.json", "sources": sources}, ensure_ascii=False, indent=2), encoding="utf-8")
    conversation = state.to_json(milestone=milestone)
    conversation["context_events"] = context_events or []
    (step_dir / "conversation_state.json").write_text(json.dumps(conversation, ensure_ascii=False, indent=2), encoding="utf-8")
    (step_dir / "tool_policy_events.json").write_text(json.dumps({"runner": runner, "milestone": milestone, "policy": tool_policy or {}, "events": tool_policy_events or [], "source_refs": ["replay.jsonl"]}, ensure_ascii=False, indent=2), encoding="utf-8")


def discover_instruction_sources(repo_root: Path) -> list[dict[str, str]]:
    candidates = [(".codex/instructions.md", "runner_config"), (".claude/CLAUDE.md", "runner_config"), ("AGENTS.md", "workspace_rule"), ("CLAUDE.md", "workspace_rule"), ("README.md", "repo_doc")]
    return [{"kind": kind, "path": rel} for rel, kind in candidates if (repo_root / rel).exists()]
