#!/usr/bin/env python3
"""Normalize runner tool calls/results into one deterministic evidence file."""
from __future__ import annotations

import json
from typing import Any


def write_jsonl(path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + ("\n" if records else ""),
        encoding="utf-8",
    )


def _parse_json_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def from_codex_events(events: list[dict[str, Any]], milestone: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    call_tools: dict[str, str] = {}
    for ev in events:
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else ev
        ptype = payload.get("type")
        timestamp = ev.get("timestamp")
        if ptype == "function_call":
            call_id = str(payload.get("call_id", ""))
            tool = str(payload.get("name", ""))
            call_tools[call_id] = tool
            records.append({
                "milestone": milestone,
                "sequence": len(records),
                "kind": "tool_call",
                "tool": tool,
                "call_id": call_id,
                "arguments": _parse_json_maybe(payload.get("arguments")),
                "timestamp": timestamp,
            })
        elif ptype == "function_call_output":
            call_id = str(payload.get("call_id", ""))
            records.append({
                "milestone": milestone,
                "sequence": len(records),
                "kind": "tool_result",
                "tool": call_tools.get(call_id, ""),
                "call_id": call_id,
                "output": _parse_json_maybe(payload.get("output")),
                "timestamp": timestamp,
            })
        else:
            item = payload.get("item") if isinstance(payload.get("item"), dict) else ev.get("item")
            if isinstance(item, dict):
                records.extend(_from_codex_item_event(ev, item, milestone, len(records)))
    return records


def _from_codex_item_event(
    ev: dict[str, Any], item: dict[str, Any], milestone: str, sequence: int
) -> list[dict[str, Any]]:
    event_type = ev.get("type", "")
    item_type = item.get("type", "")
    event_id = str(item.get("id", ev.get("id", "")))
    if event_type == "item.started" and item_type:
        arguments: dict[str, Any] = {}
        if item_type == "command_execution":
            arguments = {"command": item.get("command", "")}
        elif item_type in {"file_write", "file_edit"}:
            arguments = {"path": item.get("path", "")}
        return [{
            "milestone": milestone,
            "sequence": sequence,
            "kind": "tool_call",
            "tool": item_type,
            "call_id": event_id,
            "arguments": arguments,
            "timestamp": ev.get("timestamp"),
        }]
    if event_type == "item.completed" and item_type and item_type != "agent_message":
        return [{
            "milestone": milestone,
            "sequence": sequence,
            "kind": "tool_result",
            "tool": item_type,
            "call_id": event_id,
            "output": item.get("aggregated_output", item.get("text", "")),
            "is_error": bool(item.get("status") == "failed" or item.get("exit_code", 0) != 0),
            "exit_code": item.get("exit_code"),
            "timestamp": ev.get("timestamp"),
        }]
    return []


def from_claude_events(events: list[dict[str, Any]], milestone: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    call_tools: dict[str, str] = {}
    for ev in events:
        ev_type = ev.get("type")
        if ev_type == "assistant":
            message = ev.get("message", {})
            if not isinstance(message, dict):
                continue
            for block in message.get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                call_id = str(block.get("id", ""))
                tool = str(block.get("name", ""))
                call_tools[call_id] = tool
                records.append({
                    "milestone": milestone,
                    "sequence": len(records),
                    "kind": "tool_call",
                    "tool": tool,
                    "call_id": call_id,
                    "arguments": block.get("input"),
                })
        elif ev_type == "user":
            message = ev.get("message", {})
            if not isinstance(message, dict):
                continue
            for block in message.get("content", []) or []:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                call_id = str(block.get("tool_use_id", ""))
                records.append({
                    "milestone": milestone,
                    "sequence": len(records),
                    "kind": "tool_result",
                    "tool": call_tools.get(call_id, ""),
                    "call_id": call_id,
                    "output": ev.get("tool_use_result", block.get("content", "")),
                    "is_error": bool(block.get("is_error")),
                })
    return records


def from_tool_pairs(
    events: list[tuple[dict[str, Any] | None, dict[str, Any] | None]], milestone: str
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for tool_call, tool_result in events:
        call_id = ""
        tool = ""
        if tool_call:
            call_id = str(tool_call.get("call_id", tool_call.get("id", len(records))))
            tool = str(tool_call.get("tool", tool_call.get("name", "")))
            records.append({
                "milestone": milestone,
                "sequence": len(records),
                "kind": "tool_call",
                "tool": tool,
                "call_id": call_id,
                "arguments": tool_call,
            })
        if tool_result:
            records.append({
                "milestone": milestone,
                "sequence": len(records),
                "kind": "tool_result",
                "tool": tool,
                "call_id": call_id,
                "output": tool_result,
                "is_error": tool_result.get("ok") is False if isinstance(tool_result, dict) else None,
            })
    return records
