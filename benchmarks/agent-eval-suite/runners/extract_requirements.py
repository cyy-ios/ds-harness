#!/usr/bin/env python3
"""Deterministic requirement extraction for instruction-following scoring."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALID_SCOPES = {"current_turn", "persistent", "local_persistent"}
VALID_TYPES = {"must_do", "must_not_do", "sequence", "permission", "output_format", "scope_limit"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _prompt_text(prompt_data: dict[str, Any]) -> str:
    return str(prompt_data.get("prompt") or prompt_data.get("content") or "")


def _milestone(round_dir: Path, prompt_data: dict[str, Any], active: dict[str, Any], convo: dict[str, Any]) -> str:
    chain = convo.get("active_task_chain") if isinstance(convo.get("active_task_chain"), dict) else {}
    prompt_ms = re.search(r"里程碑\s+([A-Za-z0-9_./-]+)\s*[:：]", _prompt_text(prompt_data))
    return str(
        prompt_data.get("milestone")
        or prompt_data.get("id")
        or active.get("milestone")
        or chain.get("current_milestone")
        or (prompt_ms.group(1) if prompt_ms else "")
        or round_dir.name
    )


def _clean(value: str) -> str:
    return value.strip().strip("`'\" ")


def _strip_clause_label(text: str) -> str:
    text = _clean(text)
    for _ in range(2):
        new = re.sub(r"^(?:中断|任务|要求|提示|说明)\s*[:：]\s*", "", text)
        if new == text:
            break
        text = new
    return text


def _action_text_from_clause(clause: str, action_verbs: tuple[str, ...]) -> str:
    text = _strip_clause_label(clause)
    text = re.split(r"，当前环境|, current environment", text, maxsplit=1, flags=re.I)[0]
    m = re.search(r"(从\s+`?[\w./-]+`?\s+继续开发)", text)
    if m:
        return _clean(m.group(1))
    if any(text.startswith(verb) for verb in action_verbs):
        return text
    return ""


def _requirement(
    requirements: list[dict[str, Any]],
    *,
    milestone: str,
    req_type: str,
    text: str,
    source: str,
    scope: str = "current_turn",
    severity: str = "major",
    evidence: str = "prompt.json",
) -> None:
    text = _clean(text)
    if not text or req_type not in VALID_TYPES or scope not in VALID_SCOPES:
        return
    key = (scope, req_type, text, source)
    if any((r["scope"], r["type"], r["text"], r["source"]) == key for r in requirements):
        return
    requirements.append(
        {
            "requirement_id": f"{milestone}.r{len(requirements) + 1:03d}",
            "scope": scope,
            "type": req_type,
            "text": text,
            "source": source,
            "severity": severity,
            "evidence": evidence,
        }
    )


def _extract_prompt_requirements(prompt: str, requirements: list[dict[str, Any]], milestone: str) -> None:
    prompt_body = prompt.split("：", 1)[1] if "：" in prompt[:80] else prompt
    scope_patterns = [
        r"(只(?:改|在|动|处理)\s*`?[\w./-]+`?)",
        r"((?:only|within|under|inside)\s+`?[\w./-]+`?)",
    ]
    for pattern in scope_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            _requirement(
                requirements,
                milestone=milestone,
                req_type="scope_limit",
                text=match.group(1),
                source="prompt",
                severity="major",
            )

    flow = re.search(r"(?:先|first)\s*(.+?)(?:，再|,\s*then|再|then)\s*(.+?)(?:[。.]|$)", prompt, re.I)
    if flow:
        _requirement(
            requirements,
            milestone=milestone,
            req_type="sequence",
            text=f"{_clean(flow.group(1))} -> {_clean(flow.group(2))}",
            source="prompt",
            severity="major",
        )

    deny_patterns = [
        r"(不要\s*commit)",
        r"(不要\s*push)",
        r"(不要\s*(?:改|编辑|修改)文件)",
        r"(不要\s*(?:联网|web|搜索))",
        r"(禁止\s*[^。.;；]+)",
        r"((?:do not|don't)\s+[^.。;；]+)",
    ]
    for pattern in deny_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            text = match.group(1)
            req_type = "permission" if re.search(r"commit|push|确认|审批|approve|permission", text, re.I) else "must_not_do"
            severity = "critical" if re.search(r"commit|push|文件|destructive|reset|checkout", text, re.I) else "major"
            _requirement(
                requirements,
                milestone=milestone,
                req_type=req_type,
                text=text,
                source="prompt",
                severity=severity,
            )

    format_patterns = [
        r"(只输出\s*(?:JSON|json|表格|一句话)[^。.]*)",
        r"((?:output|respond)\s+only\s+[^.。;；]+)",
    ]
    for pattern in format_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            _requirement(
                requirements,
                milestone=milestone,
                req_type="output_format",
                text=match.group(1),
                source="prompt",
                severity="minor",
            )

    must_do_patterns = [
        r"(必须\s*[^。.;；]+)",
        r"(完成后\s*[^。.;；]+)",
    ]
    for pattern in must_do_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            _requirement(
                requirements,
                milestone=milestone,
                req_type="must_do",
                text=match.group(1),
                source="prompt",
                severity="major",
            )

    action_verbs = (
        "读取",
        "创建",
        "增加",
        "新增",
        "实现",
        "保留",
        "支持",
        "运行",
        "定位",
        "修复",
        "保持",
        "解释",
        "处理",
        "生成",
        "引用",
        "确认",
        "继续",
    )
    for clause in re.split(r"[；;。]\s*", prompt_body):
        text = _action_text_from_clause(clause, action_verbs)
        if not text or text.startswith(("不要", "禁止")):
            continue
        _requirement(
            requirements,
            milestone=milestone,
            req_type="must_do",
            text=text,
            source="prompt",
            severity="major",
        )


def _extract_conversation_requirements(convo: dict[str, Any], requirements: list[dict[str, Any]], milestone: str) -> None:
    for item in convo.get("active_local_constraints") or []:
        if item.get("status") and item.get("status") != "active":
            continue
        if item.get("kind") == "scope":
            _requirement(
                requirements,
                milestone=milestone,
                req_type="scope_limit",
                text=f"scope: {item.get('value')}",
                source="conversation_state",
                scope="local_persistent",
                severity="major",
                evidence="conversation_state.json",
            )
    for item in convo.get("active_flow_requirements") or []:
        if item.get("status") and item.get("status") != "active":
            continue
        if item.get("kind") == "ordered_steps":
            steps = [str(s) for s in item.get("steps") or [] if str(s).strip()]
            if len(steps) >= 2:
                _requirement(
                    requirements,
                    milestone=milestone,
                    req_type="sequence",
                    text=" -> ".join(steps),
                    source="conversation_state",
                    scope="local_persistent",
                    severity="major",
                    evidence="conversation_state.json",
                )
    for event in convo.get("context_events") or []:
        if event.get("event") == "context_compacted":
            _requirement(
                requirements,
                milestone=milestone,
                req_type="must_do",
                text="上下文压缩后继续遵循前序任务链和持久规则",
                source="conversation_state",
                scope="persistent",
                severity="major",
                evidence="conversation_state.json:context_events",
            )


def _extract_active_instruction_requirements(active: dict[str, Any], requirements: list[dict[str, Any]], milestone: str) -> None:
    sources = active.get("sources") or []
    if sources:
        source_text = ", ".join(str(s.get("path") or s.get("kind") or "") for s in sources if isinstance(s, dict))
        _requirement(
            requirements,
            milestone=milestone,
            req_type="must_do",
            text=f"识别并遵循已加载规则来源: {source_text}",
            source="active_instructions",
            scope="persistent",
            severity="major",
            evidence="active_instructions.json:sources",
        )


def extract_requirements_for_round(round_dir: str | Path) -> dict[str, Any]:
    round_path = Path(round_dir)
    prompt_data = _load_json(round_path / "prompt.json", {})
    active = _load_json(round_path / "active_instructions.json", {})
    convo = _load_json(round_path / "conversation_state.json", {})
    milestone = _milestone(round_path, prompt_data, active, convo)

    requirements: list[dict[str, Any]] = []
    _extract_prompt_requirements(_prompt_text(prompt_data), requirements, milestone)
    _extract_conversation_requirements(convo, requirements, milestone)
    _extract_active_instruction_requirements(active, requirements, milestone)

    return {
        "schema_version": 1,
        "milestone": milestone,
        "round_dir": round_path.name,
        "requirements": requirements,
        "source_refs": [
            name
            for name in ("prompt.json", "active_instructions.json", "conversation_state.json")
            if (round_path / name).exists()
        ],
    }


def _discover_round_dirs(evidence_root: Path) -> list[Path]:
    round_dirs = [p for p in sorted(evidence_root.glob("round_*")) if (p / "prompt.json").exists()]
    if round_dirs:
        return round_dirs
    return [p for p in sorted(evidence_root.glob("*/step_01")) if (p / "prompt.json").exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract instruction-following requirements.")
    parser.add_argument("evidence_root", help="Evidence root or single round directory")
    parser.add_argument("--write", action="store_true", help="Write requirements.json into each round directory")
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
        result = extract_requirements_for_round(round_dir)
        per_round[result["milestone"]] = result
        if args.write:
            (round_dir / "requirements.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"schema_version": 1, "rounds": len(per_round), "per_round": per_round}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
