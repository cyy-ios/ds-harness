#!/usr/bin/env python3
"""Deterministic behavior fact extraction for instruction-following scoring."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {".md", ".json", ".txt", ".log", ".yaml", ".yml", ".toml", ".py", ".csv", ".jsonl"}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _json_lines(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _target_from_tool_call(tool: str, payload: dict[str, Any]) -> str:
    if "path" in payload:
        return str(payload.get("path") or "")
    if "file_path" in payload:
        return str(payload.get("file_path") or "")
    if "filename" in payload:
        return str(payload.get("filename") or "")
    if "cmd" in payload:
        return str(payload.get("cmd") or "")
    if "command" in payload:
        return str(payload.get("command") or "")
    if "pattern" in payload:
        return str(payload.get("pattern") or "")
    return ""


def _command_from_tool_call(tool: str, payload: dict[str, Any]) -> str:
    if tool in {"shell", "exec_command", "command_execution"}:
        return str(payload.get("cmd") or payload.get("command") or "")
    return ""


def _content_excerpt(payload: dict[str, Any]) -> str:
    for key in ("content", "new_string", "old_string"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value[:2000]
    return ""


def _extract_replay(round_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    tool_calls: list[dict[str, Any]] = []
    replay_commands: list[dict[str, Any]] = []
    operation_order: list[dict[str, Any]] = []
    pending_commands: dict[str, dict[str, Any]] = {}

    for index, record in enumerate(_json_lines(round_dir / "replay.jsonl")):
        if "tool_call" in record and isinstance(record["tool_call"], dict):
            call = record["tool_call"]
            tool = str(call.get("tool") or "")
            target = _target_from_tool_call(tool, call)
            item = {
                "index": index,
                "tool": tool,
                "target": target,
                "input": {k: v for k, v in call.items() if k not in {"content"}},
            }
            excerpt = _content_excerpt(call)
            if excerpt:
                item["content_excerpt"] = excerpt
            tool_calls.append(item)
            operation_order.append({"index": index, "kind": "tool_call", "tool": tool, "target": target})
            command = _command_from_tool_call(tool, call)
            if command:
                replay_commands.append({"index": index, "command": command, "cwd": "", "exit_code": None, "stdout_excerpt": "", "source": "replay.jsonl"})
            continue

        if record.get("event_type") == "tool_call":
            tool = str(record.get("tool") or "")
            payload = record.get("tool_input") if isinstance(record.get("tool_input"), dict) else {}
            target = _target_from_tool_call(tool, payload)
            event_id = str(record.get("event_id") or index)
            item = {
                "index": index,
                "step": record.get("step"),
                "tool": tool,
                "target": target,
                "input": payload,
            }
            excerpt = _content_excerpt(payload)
            if excerpt:
                item["content_excerpt"] = excerpt
            tool_calls.append(item)
            operation_order.append({"index": index, "kind": "tool_call", "tool": tool, "target": target})
            command = _command_from_tool_call(tool, payload)
            if command:
                pending_commands[event_id] = {"index": index, "command": command, "cwd": "", "exit_code": None, "stdout_excerpt": "", "source": "replay.jsonl"}
                replay_commands.append(pending_commands[event_id])
            continue

        if record.get("event_type") == "tool_result":
            event_id = str(record.get("event_id") or "")
            output = str(record.get("tool_output") or "")[:2000]
            if event_id in pending_commands:
                pending_commands[event_id]["exit_code"] = 1 if record.get("tool_error") else 0
                pending_commands[event_id]["stdout_excerpt"] = output
            operation_order.append({"index": index, "kind": "tool_result", "tool": str(record.get("tool") or ""), "target": event_id})
            continue

        if record.get("event_type") == "agent_message":
            text = str(record.get("assistant_text") or "")
            operation_order.append({"index": index, "kind": "agent_message", "tool": "", "target": text[:120]})

    return tool_calls, replay_commands, operation_order


def _extract_commands(round_dir: Path, replay_commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _read_text(round_dir / "commands.log").strip()
    commands: list[dict[str, Any]] = []
    if text:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                commands.append(
                    {
                        "index": index,
                        "command": str(item.get("command") or item.get("cmd") or ""),
                        "cwd": str(item.get("cwd") or ""),
                        "exit_code": item.get("exit_code") if item.get("exit_code") is not None else item.get("returncode"),
                        "stdout_excerpt": str(item.get("stdout") or item.get("output") or "")[:2000],
                        "source": "commands.log",
                    }
                )
        else:
            for index, line in enumerate(text.splitlines()):
                line = line.strip()
                if not line:
                    continue
                commands.append({"index": index, "command": line, "cwd": "", "exit_code": None, "stdout_excerpt": "", "source": "commands.log"})

    if not commands:
        return replay_commands

    seen = {cmd["command"] for cmd in commands if cmd["command"]}
    for cmd in replay_commands:
        if cmd["command"] and cmd["command"] not in seen:
            commands.append(cmd)
            seen.add(cmd["command"])
    return commands


def _extract_diff_files(round_dir: Path) -> list[dict[str, Any]]:
    text = _read_text(round_dir / "diff.patch")
    if not text.strip() or text.strip() == "(no changes)":
        return []
    files: list[dict[str, Any]] = []
    by_path: dict[str, dict[str, Any]] = {}
    current_path = ""
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                current_path = parts[3][2:] if parts[3].startswith("b/") else parts[3]
                by_path.setdefault(current_path, {"path": current_path, "change_type": "modified", "source": "diff.patch"})
        elif line.startswith("new file mode"):
            if current_path:
                by_path.setdefault(current_path, {"path": current_path, "change_type": "modified", "source": "diff.patch"})
                by_path[current_path]["change_type"] = "added"
        elif line.startswith("deleted file mode"):
            if current_path:
                by_path.setdefault(current_path, {"path": current_path, "change_type": "modified", "source": "diff.patch"})
                by_path[current_path]["change_type"] = "deleted"
        elif line.startswith("+++ b/"):
            path = line[len("+++ b/") :]
            if path:
                current_path = path
                by_path.setdefault(path, {"path": path, "change_type": "modified", "source": "diff.patch"})
    return list(by_path.values())


def _extract_replay_edited_files(tool_calls: list[dict[str, Any]], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {item["path"] for item in existing}
    out = list(existing)
    for call in tool_calls:
        if call["tool"] not in {"write_file", "file_write", "edit", "file_edit", "apply_patch"}:
            continue
        target = call.get("target") or ""
        if target and target not in seen:
            out.append({"path": target, "change_type": "unknown", "source": "replay.jsonl"})
            seen.add(target)
    return out


def _extract_artifacts(round_dir: Path) -> list[dict[str, Any]]:
    artifact_dir = round_dir / "artifact"
    if not artifact_dir.is_dir():
        return []
    artifacts = []
    for path in sorted(p for p in artifact_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(artifact_dir).as_posix()
        artifacts.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "text": path.read_text(encoding="utf-8", errors="replace")[:1000] if path.suffix.lower() in TEXT_EXTENSIONS else "",
            }
        )
    return artifacts


def _extract_final_claims(round_dir: Path) -> list[dict[str, Any]]:
    text = _read_text(round_dir / "response.md")
    claims = []
    parts = [p.strip() for p in re.split(r"[\n。]+", text) if p.strip()]
    for index, part in enumerate(parts):
        claims.append({"index": index, "text": part[:1000], "source": "response.md"})
    return claims


def _milestone(round_dir: Path) -> str:
    prompt_path = round_dir / "prompt.json"
    if prompt_path.exists():
        try:
            prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prompt = {}
        text = str(prompt.get("prompt") or "")
        m = re.search(r"里程碑\s+([A-Za-z0-9_./-]+)\s*[:：]", text)
        return str(prompt.get("milestone") or prompt.get("id") or (m.group(1) if m else "") or round_dir.parent.name)
    return round_dir.parent.name if round_dir.name == "step_01" else round_dir.name


def extract_behavior_facts_for_round(round_dir: str | Path) -> dict[str, Any]:
    round_path = Path(round_dir)
    tool_calls, replay_commands, operation_order = _extract_replay(round_path)
    commands = _extract_commands(round_path, replay_commands)
    edited_files = _extract_replay_edited_files(tool_calls, _extract_diff_files(round_path))
    return {
        "schema_version": 1,
        "milestone": _milestone(round_path),
        "round_dir": round_path.name,
        "tool_calls": tool_calls,
        "commands": commands,
        "edited_files": edited_files,
        "artifacts": _extract_artifacts(round_path),
        "final_claims": _extract_final_claims(round_path),
        "operation_order": operation_order,
        "source_refs": [
            name
            for name in ("replay.jsonl", "commands.log", "diff.patch", "artifact", "response.md")
            if (round_path / name).exists()
        ],
    }


def _discover_round_dirs(evidence_root: Path) -> list[Path]:
    round_dirs = [p for p in sorted(evidence_root.glob("round_*")) if (p / "replay.jsonl").exists() or (p / "response.md").exists()]
    if round_dirs:
        return round_dirs
    return [p for p in sorted(evidence_root.glob("*/step_01")) if (p / "replay.jsonl").exists() or (p / "response.md").exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract behavior facts for instruction-following scoring.")
    parser.add_argument("evidence_root", help="Evidence root or single round directory")
    parser.add_argument("--write", action="store_true", help="Write behavior_facts.json into each round directory")
    args = parser.parse_args()

    root = Path(args.evidence_root).resolve()
    if not root.exists():
        print(json.dumps({"error": f"path not found: {root}"}, ensure_ascii=False))
        sys.exit(1)
    round_dirs = [root] if (root / "prompt.json").exists() else _discover_round_dirs(root)
    if not round_dirs:
        print(json.dumps({"error": f"no evidence rounds under {root}"}, ensure_ascii=False))
        sys.exit(1)

    per_round = {}
    for round_dir in round_dirs:
        result = extract_behavior_facts_for_round(round_dir)
        per_round[result["milestone"]] = result
        if args.write:
            (round_dir / "behavior_facts.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"schema_version": 1, "rounds": len(per_round), "per_round": per_round}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
