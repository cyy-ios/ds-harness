#!/usr/bin/env python3
"""Lightweight context evidence for instruction-following scoring."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_SCOPE_RE = re.compile(
    r"(?:under|within|inside|only in|只(?:在|改)|范围(?:是|:|：)?)\s+(`?[\w./-]+`?)",
    re.I,
)
_FLOW_RE = re.compile(r"(?:first|先)\s+(.+?)(?:,\s*then|，再|再|then)\s+(.+?)(?:[.。]|$)", re.I)


def _clean(value: str) -> str:
    return value.strip().strip("`'\" ")


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
        if any(word in lower for word in ("撤销", "取消", "reset", "ignore previous")):
            self.active_local_constraints.clear()
            self.active_flow_requirements.clear()

        for match in _SCOPE_RE.finditer(prompt):
            value = _clean(match.group(1))
            if value and not self._has_constraint("scope", value):
                self.active_local_constraints.append(
                    {
                        "kind": "scope",
                        "value": value,
                        "source": milestone,
                        "status": "active",
                    }
                )

        flow = _FLOW_RE.search(prompt)
        if flow:
            steps = [_clean(flow.group(1)), _clean(flow.group(2))]
            self.active_flow_requirements.append(
                {
                    "kind": "ordered_steps",
                    "steps": steps,
                    "source": milestone,
                    "status": "active",
                }
            )

    def _has_constraint(self, kind: str, value: str) -> bool:
        return any(c.get("kind") == kind and c.get("value") == value for c in self.active_local_constraints)

    def to_json(self, *, milestone: str) -> dict[str, Any]:
        return {
            "active_task_chain": {
                "current_milestone": milestone,
                "previous_milestone": self.previous_milestone,
            },
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
    """Write non-duplicative context evidence next to the raw per-round files."""
    state.update_from_prompt(milestone=milestone, prompt=prompt)
    sources = instruction_sources if instruction_sources is not None else discover_instruction_sources(repo_root)

    (step_dir / "active_instructions.json").write_text(
        json.dumps(
            {
                "runner": runner,
                "milestone": milestone,
                "prompt_ref": "prompt.json",
                "sources": sources,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    conversation = state.to_json(milestone=milestone)
    conversation["context_events"] = context_events or []
    (step_dir / "conversation_state.json").write_text(
        json.dumps(conversation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (step_dir / "tool_policy_events.json").write_text(
        json.dumps(
            {
                "runner": runner,
                "milestone": milestone,
                "policy": tool_policy or {},
                "events": tool_policy_events or [],
                "source_refs": ["replay.jsonl"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def discover_instruction_sources(repo_root: Path) -> list[dict[str, str]]:
    candidates = [
        (".codex/instructions.md", "runner_config"),
        (".claude/CLAUDE.md", "runner_config"),
        ("AGENTS.md", "workspace_rule"),
        ("CLAUDE.md", "workspace_rule"),
        ("README.md", "repo_doc"),
    ]
    sources = []
    for rel, kind in candidates:
        if (repo_root / rel).exists():
            sources.append({"kind": kind, "path": rel})
    return sources
