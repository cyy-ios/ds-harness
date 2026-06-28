#!/usr/bin/env python3
"""Lightweight context evidence for following scoring."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_context_evidence(
    step_dir: Path,
    *,
    runner: str,
    milestone: str,
    prompt: str,
    repo_root: Path,
    instruction_sources: list[dict[str, str]] | None = None,
    tool_policy: dict[str, Any] | None = None,
    tool_policy_events: list[dict[str, Any]] | None = None,
    context_events: list[dict[str, Any]] | None = None,
) -> None:
    sources = instruction_sources if instruction_sources is not None else discover_instruction_sources(repo_root)
    (step_dir / "active_instructions.json").write_text(
        json.dumps(
            {
                "runner": runner,
                "milestone": milestone,
                "prompt_ref": "prompt.json",
                "sources": sources,
                "context_events": context_events or [],
            },
            ensure_ascii=False,
            indent=2,
        ),
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
    return [{"kind": kind, "path": rel} for rel, kind in candidates if (repo_root / rel).exists()]
