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

from evidence_context import ConversationState, write_context_evidence
from run_codex_replay import (
    _milestone_index,
    _normalize_tool_output,
    _run_acceptance,
    _run_analyzer,
    load_compact_summary,
    reject_benchmark_results_path,
    resolve_deepseek_api_key,
)


CLAUDE_ALLOWED_TOOLS = (
    "Task,AskUserQuestion,Bash,PowerShell,Read,Write,Edit,MultiEdit,Glob,Grep,LS"
)


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


def build_replay_jsonl(events: list[dict[str, Any]], ms_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tool_names: dict[str, str] = {}
    step = 0
    for ev in events:
        ev_type = ev.get("type")
        if ev_type == "assistant":
            message = ev.get("message", {})
            if not isinstance(message, dict):
                continue
            for block in message.get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        records.append({
                            "milestone": ms_id,
                            "step": step,
                            "assistant_text": text,
                            "event_type": "agent_message",
                        })
                        step += 1
                elif block.get("type") == "tool_use":
                    tool_id = str(block.get("id", ""))
                    name = str(block.get("name", ""))
                    tool_names[tool_id] = name
                    records.append({
                        "milestone": ms_id,
                        "step": step,
                        "tool": _tool_item_type(name),
                        "tool_input": _tool_input_for_replay(name, block.get("input")),
                        "event_type": "tool_call",
                        "event_id": tool_id,
                    })
                    step += 1
        elif ev_type == "user":
            message = ev.get("message", {})
            if not isinstance(message, dict):
                continue
            for block in message.get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_id = str(block.get("tool_use_id", ""))
                name = tool_names.get(tool_id, "")
                result = ev.get("tool_use_result")
                output = block.get("content", "")
                if isinstance(result, dict):
                    stdout = result.get("stdout", "")
                    stderr = result.get("stderr", "")
                    shell_output = "\n".join(str(part) for part in [stdout, stderr] if part)
                    if shell_output:
                        output = shell_output
                    elif not output:
                        output = json.dumps(result, ensure_ascii=False)
                records.append({
                    "milestone": ms_id,
                    "step": step,
                    "tool": _tool_item_type(name),
                    "tool_output": _normalize_tool_output(name, output),
                    "tool_error": bool(block.get("is_error")),
                    "event_type": "tool_result",
                    "event_id": tool_id,
                })
                step += 1
        elif ev_type == "result":
            records.append({
                "milestone": ms_id,
                "step": step,
                "event_type": "turn.completed",
                "usage": ev.get("usage"),
                "stop_reason": ev.get("stop_reason"),
            })
            step += 1
    return records


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


def extract_command_log(records: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for record in records:
        if record.get("event_type") == "tool_call" and record.get("tool") == "shell":
            inp = record.get("tool_input", {})
            command = inp.get("command", "") if isinstance(inp, dict) else ""
            lines.append(f"$ {command}")
        elif record.get("event_type") == "tool_result" and record.get("tool") == "shell":
            lines.append(str(record.get("tool_output", "")))
            lines.append(f"[error: {record.get('tool_error')}]")
            lines.append("")
    return "\n".join(lines)


def extract_usage_tokens(events: list[dict[str, Any]]) -> tuple[int, int]:
    input_tokens = 0
    output_tokens = 0
    for ev in events:
        usage = ev.get("usage")
        if isinstance(usage, dict):
            input_tokens += int(usage.get("input_tokens", 0) or 0)
            output_tokens += int(usage.get("output_tokens", 0) or 0)
        message = ev.get("message")
        if isinstance(message, dict):
            usage = message.get("usage")
            if isinstance(usage, dict):
                input_tokens += int(usage.get("input_tokens", 0) or 0)
                output_tokens += int(usage.get("output_tokens", 0) or 0)
    return input_tokens, output_tokens


def run_claude(
    prompt: str,
    *,
    cwd: Path,
    session_id: str | None,
    extra_context: str = "",
    model: str,
    timeout: int,
) -> tuple[list[dict[str, Any]], str | None, subprocess.CompletedProcess[str]]:
    full_prompt = f"{extra_context}\n\n---\n\n{prompt}" if extra_context else prompt
    claude_bin = shutil.which("claude.cmd") or shutil.which("claude") or "claude"
    cmd = [
        claude_bin,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        model,
        "--permission-mode",
        "bypassPermissions",
        "--allowedTools",
        CLAUDE_ALLOWED_TOOLS,
    ]
    if session_id:
        cmd.extend(["--resume", session_id])

    env = os.environ.copy()
    api_key = resolve_deepseek_api_key()
    env.update({
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_AUTH_TOKEN": api_key,
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": model,
        "CLAUDE_CODE_SUBAGENT_MODEL": model,
        "CLAUDE_CODE_EFFORT_LEVEL": "max",
    })

    result = subprocess.run(
        cmd,
        input=full_prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=cwd,
        env=env,
    )
    events = parse_jsonl(result.stdout) or parse_jsonl(result.stderr)
    return events, extract_session_id(events) or session_id, result


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
    conversation_state: ConversationState | None = None,
) -> Path:
    step_dir = evidence_root / ms_id / "step_01"
    step_dir.mkdir(parents=True, exist_ok=True)

    records = build_replay_jsonl(events, ms_id)
    (step_dir / "replay.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )
    (step_dir / "response.md").write_text(extract_response_text(events), encoding="utf-8")
    (step_dir / "prompt.json").write_text(
        json.dumps({"id": ms_id, "prompt": ms_prompt}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_context_evidence(
        step_dir,
        runner="claude_code_cli",
        milestone=ms_id,
        prompt=ms_prompt,
        repo_root=repo_root,
        state=conversation_state or ConversationState(),
        instruction_sources=[{"kind": "runner_config", "path": ".claude/CLAUDE.md"}],
        tool_policy={
            "allowed_tools": CLAUDE_ALLOWED_TOOLS.split(","),
            "model": "deepseek_anthropic_compatible",
        },
    )
    (step_dir / "commands.log").write_text(extract_command_log(records), encoding="utf-8")

    subprocess.run(["git", "add", "-A"], capture_output=True, cwd=repo_root, timeout=30)
    full_diff = subprocess.run(
        ["git", "diff", "--cached", "HEAD", "-p"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=repo_root,
        timeout=30,
    )
    (step_dir / "diff.patch").write_text(full_diff.stdout or "(no changes)", encoding="utf-8")

    round_id = f"round_{_milestone_index(ms_id):02d}"
    acceptance = _run_acceptance(repo_root, round_id=round_id, milestone=ms_id)
    (step_dir / "acceptance.json").write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (step_dir / "compact_trigger.json").write_text(
        json.dumps({"triggered": False, "summary_meta": compact_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    artifact_dst = step_dir / "artifact"
    if artifact_dst.exists():
        shutil.rmtree(artifact_dst)
    artifact_src = repo_root / "reports"
    if artifact_src.exists():
        shutil.copytree(artifact_src, artifact_dst)
    else:
        artifact_dst.mkdir(exist_ok=True)

    snap_dst = step_dir / "source_snapshot"
    if snap_dst.exists():
        shutil.rmtree(snap_dst)
    snap_dst.mkdir()
    for sub in ["src", "tests", "skills"]:
        sub_dir = repo_root / sub
        if sub_dir.is_dir():
            shutil.copytree(sub_dir, snap_dst / sub, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    tokens_in, tokens_out = extract_usage_tokens(events)
    (step_dir / "cost.json").write_text(
        json.dumps({
            "elapsed_sec": round(elapsed, 2),
            "input_tokens": tokens_in,
            "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "tool_steps": sum(1 for r in records if r.get("event_type") == "tool_call"),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _run_analyzer(step_dir)
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
    conversation_state = ConversationState()

    for offset, ms in enumerate(milestones):
        ms_id = ms["id"]
        prompt = ms["prompt"]
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
        step_dir = collect_evidence(out, ms_id, events, prompt, root, elapsed, compact_meta, conversation_state)
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

    (out / "run_summary.json").write_text(
        json.dumps({
            "runner": "claude_code_cli",
            "variant": "claude-deepseek",
            "model": args.model,
            "root": str(root),
            "evidence_root": str(out),
            "milestones_completed": len(results),
            "results": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
