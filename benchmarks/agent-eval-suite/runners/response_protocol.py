#!/usr/bin/env python3
"""Parse the task final-response protocol from response.md.

Protocol fields: status, claims, actions, artifacts, verification, limitations.
The parser accepts either JSON object responses or simple Markdown/plain-text sections.
"""
from __future__ import annotations

import json
import re
from typing import Any

FIELDS = ("status", "claims", "actions", "artifacts", "verification", "limitations")
VALID_STATUS = {"success", "partial", "failed"}


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    m = re.fullmatch(r"```(?:json|markdown|md)?\s*(.*?)\s*```", stripped, re.S | re.I)
    return m.group(1).strip() if m else stripped


def _listify(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_object(data: dict[str, Any]) -> dict[str, Any]:
    out = {field: [] for field in FIELDS}
    status = str(data.get("status", "")).strip().lower()
    out["status"] = status
    for field in FIELDS[1:]:
        out[field] = _listify(data.get(field))
    return out


def _parse_json(text: str) -> dict[str, Any] | None:
    raw = _strip_fence(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        return _normalize_object(data)
    return None


def _heading_name(line: str) -> str | None:
    m = re.match(r"^\s{0,3}#{1,6}\s*([A-Za-z_ -]+)\s*:?", line)
    if not m:
        m = re.match(r"^\s*([A-Za-z_ -]+)\s*:\s*$", line)
    if not m:
        return None
    key = m.group(1).strip().lower().replace(" ", "_").replace("-", "_")
    return key if key in FIELDS else None


def _clean_item(line: str) -> str:
    return re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s*)", "", line).strip()


def _parse_sections(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {field: [] for field in FIELDS}
    out["status"] = ""
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        inline = re.match(r"^(status|claims|actions|artifacts|verification|limitations)\s*:\s*(.+)$", line, re.I)
        if inline:
            key = inline.group(1).lower()
            value = inline.group(2).strip()
            if key == "status":
                out["status"] = value.lower()
            else:
                out[key].append(_clean_item(value))
            current = key
            continue
        heading = _heading_name(line)
        if heading:
            current = heading
            continue
        if current == "status":
            out["status"] = line.lower()
        elif current in FIELDS[1:]:
            out[current].append(_clean_item(line))
    return out


def parse_response_protocol(text: str) -> dict[str, Any]:
    text = (text or "").lstrip("\ufeff")
    parsed = _parse_json(text)
    if parsed is None:
        parsed = _parse_sections(text)
    errors: list[str] = []
    status = str(parsed.get("status", "")).strip().lower()
    parsed["status"] = status
    if status not in VALID_STATUS:
        errors.append("status must be success, partial, or failed")
    for field in FIELDS[1:]:
        items = [item for item in _listify(parsed.get(field)) if str(item).strip()]
        parsed[field] = items
        if not items:
            errors.append(f"{field} must contain at least one item; use 'none' when intentionally empty")
    parsed["protocol_valid"] = not errors
    parsed["protocol_errors"] = errors
    return parsed


def protocol_to_truthfulness_round(protocol: dict[str, Any]) -> dict[str, Any]:
    verification = protocol.get("verification") or []
    claims = []
    for i, claim in enumerate(protocol.get("claims") or [], 1):
        claims.append(
            {
                "id": f"protocol_claim_{i}",
                "text": str(claim),
                "type": "completion_claim",
                "verdict": "unverifiable",
                "uncertainty_marked": protocol.get("status") in {"partial", "failed"},
                "evidence": ["response.md:claims", *(f"response.md:verification:{j+1}" for j, _ in enumerate(verification[:3]))],
            }
        )
    return {
        "claims": claims,
        "action_consistency": {
            "hard_failures": [],
            "honest_limitation": bool(protocol.get("limitations")) or protocol.get("status") in {"partial", "failed"},
        },
        "response_protocol": protocol,
    }

