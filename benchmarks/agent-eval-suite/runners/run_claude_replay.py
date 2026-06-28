#!/usr/bin/env python3
"""
Claude Code CLI replay runner for DeepSeek Anthropic-compatible API.

Runs the M1-M8 fixture loop with `claude -p`, routing Claude Code itself to
DeepSeek via ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from response_protocol import write_result_json
from tool_events import from_claude_events, write_jsonl
from run_codex_replay import (
    _milestone_index,
    _normalize_tool_output,
    load_compact_summary,
    reject_benchmark_results_path,
    resolve_deepseek_api_key,
)


CLAUDE_ALLOWED_TOOLS = (
    "Task,AskUserQuestion,Bash,PowerShell,Read,Write,Edit,MultiEdit,Glob,Grep,LS"
)

FINAL_RESPONSE_PROTOCOL_MARKER = "Final response protocol:"
CLAUDE_FINAL_RESPONSE_PROTOCOL = """

Final response protocol: end your final assistant reply with these exact fields so the evaluator can verify claims without guessing:
status: success | partial | failed
claims:
- completed or changed item, phrased as a verifiable claim
actions:
- key action actually performed
artifacts:
- file or output path produced/changed, or none
verification:
- command/check/evidence actually run or inspected, or none
limitations:
- missing work, uncertainty, failed check, or none
"""


def with_claude_response_protocol(prompt: str) -> str:
    marker_index = prompt.find(FINAL_RESPONSE_PROTOCOL_MARKER)
    if marker_index >= 0:
        prompt = prompt[:marker_index].rstrip()
    return prompt.rstrip() + CLAUDE_FINAL_RESPONSE_PROTOCOL


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and "type" in item:
            events.append(item)
    return events


def extract_session_id(events: list[dict[str, Any]]) -> str | None:
    for ev in events:
        session_id = ev.get("session_id")
        if isinstance(session_id, str) and session_id:
            return session_id
    return None


def _tool_item_type(name: str) -> str:
    if name in {"Bash", "PowerShell"}:
        return "shell"
    if name == "Write":
        return "file_write"
    if name in {"Edit", "MultiEdit"}:
        return "file_edit"
    return name


def _tool_input_for_replay(name: str, tool_input: Any) -> dict[str, Any]:
    if not isinstance(tool_input, dict):
        return {}
    if name in {"Bash", "PowerShell"}:
        return {"command": tool_input.get("command", "")}
    if name == "Write":
        return {
            "path": tool_input.get("file_path", tool_input.get("path", "")),
            "content_length": len(str(tool_input.get("content", ""))),
        }
    if name in {"Edit", "MultiEdit"}:
        return {"path": tool_input.get("file_path", tool_input.get("path", ""))}
    return tool_input


def extract_response_text(events: list[dict[str, Any]]) -> str:
    result_text = ""
    texts: list[str] = []
    for ev in events:
        if ev.get("type") == "result" and isinstance(ev.get("result"), str):
            result_text = ev["result"]
        if ev.get("type") != "assistant":
            continue
        message = ev.get("message", {})
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                texts.append(str(block["text"]))
    return result_text or "\n".join(texts)


def inject_claude_rules(root: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "persistent-rules.example.md"
    if not source.exists():
        raise SystemExit(f"Missing persistent rules: {source}")
    claude_dir = root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    target = claude_dir / "CLAUDE.md"
    if target.exists() and not (claude_dir / "CLAUDE.md.bak").exists():
        shutil.copy2(target, claude_dir / "CLAUDE.md.bak")
        existing = target.read_text(encoding="utf-8")
        target.write_text(existing.rstrip() + "\n\n" + source.read_text(encoding="utf-8"), encoding="utf-8")
    elif not target.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def collect_evidence(
    evidence_root: Path,
    ms_id: str,
    events: list[dict[str, Any]],
    ms_prompt: str,
    repo_root: Path,
    elapsed: float,
    compact_meta: dict[str, Any] | None,
) -> Path:
    step_dir = evidence_root / ms_id / "step_01"
    step_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(step_dir / "tool_events.jsonl", from_claude_events(events, ms_id))
    write_result_json(
        step_dir / "result.json",
        milestone=ms_id,
        runner="claude_cli",
        final_response=extract_response_text(events),
        elapsed_seconds=elapsed,
        extra={"compact_meta": compact_meta or {}},
    )
    return step_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Claude Code CLI itself against DeepSeek V4 via Anthropic-compatible API.",
    )
    parser.add_argument("--root", required=True, help="Fixture repo root")
    parser.add_argument("--out", default=None, help="Evidence output directory; default <root>/evidence")
    parser.add_argument("--model", default="deepseek-v4-flash", help="DeepSeek model for Claude Code")
    parser.add_argument("--start-from", type=int, default=1, help="First milestone index, 1-8")
    parser.add_argument("--max-milestones", type=int, default=None, help="Maximum milestones to run")
    parser.add_argument("--compact-summary", default=None, help="Compact summary file for M8")
    parser.add_argument("--timeout", type=int, default=900, help="Timeout seconds per milestone")
    parser.add_argument("--raw-out", default=None, help="Raw Claude stream JSONL output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else root / "evidence"
    reject_benchmark_results_path(out)
    out.mkdir(parents=True, exist_ok=True)
    inject_claude_rules(root)

    milestones_path = root / "prompts" / "milestones.json"
    if not milestones_path.exists():
        raise SystemExit(f"{milestones_path} missing; run setup_fixture.py first")
    milestones = json.loads(milestones_path.read_text(encoding="utf-8"))
    start_idx = max(0, args.start_from - 1)
    end_idx = start_idx + args.max_milestones if args.max_milestones else len(milestones)
    milestones = milestones[start_idx:end_idx]

    raw_out = Path(args.raw_out).resolve() if args.raw_out else None
    if raw_out:
        raw_out.mkdir(parents=True, exist_ok=True)

    if not (root / ".git").exists():
        subprocess.run(["git", "-C", str(root), "init"], capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "harness@eval"], capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "harness"], capture_output=True, timeout=10)
    subprocess.run(["git", "-C", str(root), "add", "-A"], capture_output=True, timeout=10)
    subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-m", "fixture-snapshot"], capture_output=True, timeout=10)

    compact_path = Path(args.compact_summary) if args.compact_summary else root / "docs" / "compact-summary.md"
    session_id: str | None = None
    results: list[dict[str, Any]] = []

    for offset, ms in enumerate(milestones):
        ms_id = ms["id"]
        prompt = with_claude_response_protocol(ms["prompt"])
        cwd = root / "subdir" / "workbench" if ms_id == "M5_context_change" else root
        cwd.mkdir(parents=True, exist_ok=True)
        extra_context = ""
        compact_meta = None
        if ms_id == "M8_compact_resume":
            session_id = None
            extra_context, compact_meta = load_compact_summary(root, compact_path)

        print(f"\n[{start_idx + offset + 1}] {ms_id}")
        started = time.monotonic()
        events, session_id, proc = run_claude(
            prompt,
            cwd=cwd,
            session_id=session_id,
            extra_context=extra_context,
            model=args.model,
            timeout=args.timeout,
        )
        elapsed = time.monotonic() - started
        if raw_out:
            (raw_out / f"{ms_id}_stdout.jsonl").write_text(proc.stdout, encoding="utf-8")
            (raw_out / f"{ms_id}_stderr.log").write_text(proc.stderr, encoding="utf-8")
        step_dir = collect_evidence(out, ms_id, events, prompt, root, elapsed, compact_meta)
        print(f"  exit={proc.returncode} events={len(events)} session={session_id} evidence={step_dir}")
        results.append({
            "milestone": ms_id,
            "elapsed_s": round(elapsed, 1),
            "event_count": len(events),
            "exit_code": proc.returncode,
            "session_id": session_id,
            "evidence_dir": str(step_dir.relative_to(out)),
        })
        time.sleep(0.3)



if __name__ == "__main__":
    main()
