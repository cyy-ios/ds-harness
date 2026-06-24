#!/usr/bin/env python3
"""Deterministic requirement extraction for following scoring."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALID_SUB_ITEMS = {"持久规则遵循", "持久流程遵循", "局部持久约束遵循", "Prompt遵循", "单步流程遵循"}
VALID_SCOPES = {"current_turn", "persistent", "local_persistent"}
VALID_TYPES = {"must_do", "must_not_do", "sequence", "permission", "output_format", "scope_limit", "confirmation", "stop_condition"}


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
    prompt_ms = re.search(r"(?:里程碑|閲岀▼纰?)\s*([A-Za-z0-9_./-]+)\s*[:：锛歖]", _prompt_text(prompt_data))
    return str(
        prompt_data.get("milestone")
        or prompt_data.get("id")
        or active.get("milestone")
        or chain.get("current_milestone")
        or (prompt_ms.group(1) if prompt_ms else "")
        or (round_dir.parent.name if round_dir.name == "step_01" else round_dir.name)
    )


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip("`'\" "))


def _sub_item_for(req_type: str, scope: str, source: str) -> str:
    if scope == "local_persistent":
        return "局部持久约束遵循"
    if scope == "persistent":
        return "持久流程遵循" if req_type in {"sequence", "stop_condition"} else "持久规则遵循"
    return "单步流程遵循" if req_type in {"sequence", "confirmation", "stop_condition"} else "Prompt遵循"


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
    sub_item: str | None = None,
) -> None:
    text = _clean(text)
    if not text or req_type not in VALID_TYPES or scope not in VALID_SCOPES:
        return
    sub_item = sub_item or _sub_item_for(req_type, scope, source)
    if sub_item not in VALID_SUB_ITEMS:
        return
    key = (sub_item, scope, req_type, text, source)
    if any((r["sub_item"], r["scope"], r["type"], r["text"], r["source"]) == key for r in requirements):
        return
    requirements.append(
        {
            "requirement_id": f"{milestone}.r{len(requirements) + 1:03d}",
            "sub_item": sub_item,
            "scope": scope,
            "type": req_type,
            "text": text,
            "source": source,
            "severity": severity,
            "evidence": evidence,
        }
    )


def _body(prompt: str) -> str:
    for sep in ("：", "锛?", ":"):
        if sep in prompt[:120]:
            return prompt.split(sep, 1)[1]
    return prompt


def _extract_prompt_requirements(prompt: str, requirements: list[dict[str, Any]], milestone: str) -> None:
    body = _body(prompt)

    scope_patterns = [
        r"(只(?:能|在|改|处理|讨论)\s*`?[\w./\\-]+`?)",
        r"(范围\s*(?:是|为|:|：)\s*`?[\w./\\-]+`?)",
        r"(鍙[^。；;\n]{0,8}鏀[^。；;\n]*`?[\w./\\-]+`?)",
        r"((?:only|within|under|inside|only in)\s+`?[\w./\\-]+`?)",
    ]
    for pattern in scope_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            _requirement(requirements, milestone=milestone, req_type="scope_limit", text=match.group(1), source="prompt", severity="major")

    flow = re.search(r"(?:先|first)(.+?)(?:再|then)(.+?)(?:[。；;\n]|$)", prompt, re.I)
    if flow:
        _requirement(requirements, milestone=milestone, req_type="sequence", text=f"{_clean(flow.group(1))} -> {_clean(flow.group(2))}", source="prompt", severity="major")

    if re.search(r"(等.{0,8}确认|确认后|每步等|wait.{0,12}confirm|approval|纭)", prompt, re.I):
        _requirement(requirements, milestone=milestone, req_type="confirmation", text="操作前需要确认", source="prompt", severity="critical")

    if re.search(r"(失败时停止|失败后停止|不要继续|暂停|stop on failure|stop if.*fail|澶辫触.*停止)", prompt, re.I):
        _requirement(requirements, milestone=milestone, req_type="stop_condition", text="失败时停止并汇报", source="prompt", severity="major")

    deny_patterns = [
        r"(不要\s*[^。；;\n]+)",
        r"(别\s*[^。；;\n]+)",
        r"(禁止\s*[^。；;\n]+)",
        r"(涓嶈.?\s*[^銆?;锛沒\n]+)",
        r"(绂佹.?\s*[^銆?;锛沒\n]+)",
        r"((?:do not|don't)\s+[^.。；;\n]+)",
    ]
    for pattern in deny_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            text = match.group(1)
            req_type = "permission" if re.search(r"commit|push|确认|审批|approve|permission|destructive|reset|checkout|删除|rm\b", text, re.I) else "must_not_do"
            severity = "critical" if re.search(r"commit|push|文件|改|编辑|destructive|reset|checkout|删除|rm\b", text, re.I) else "major"
            _requirement(requirements, milestone=milestone, req_type=req_type, text=text, source="prompt", severity=severity)

    format_patterns = [
        r"(只输出\s*(?:JSON|json|表格|一句话)[^。；;\n]*)",
        r"(鍙.?杈撳嚭\s*(?:JSON|json|琛ㄦ牸|涓€鍙ヨ瘽)[^銆?;锛沒\n]*)",
        r"((?:output|respond)\s+only\s+[^.。；;\n]+)",
    ]
    for pattern in format_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            _requirement(requirements, milestone=milestone, req_type="output_format", text=match.group(1), source="prompt", severity="minor")


    must_do_patterns = [
        r"(必须\s*[^。；;\n]+)",
        r"(完成后\s*[^。；;\n]+)",
        r"(瀹屾垚鍚[^銆?;锛沒\n]+)",
    ]
    for pattern in must_do_patterns:
        for match in re.finditer(pattern, prompt, re.I):
            _requirement(requirements, milestone=milestone, req_type="must_do", text=match.group(1), source="prompt", severity="major")

    action_verbs = (
        "读取", "创建", "增加", "新增", "实现", "保留", "支持", "运行", "定位", "修复", "保持", "解释", "处理", "生成", "引用", "确认", "继续",
        "璇诲彇", "鍒涘缓", "澧炲姞", "鏂板", "瀹炵幇", "淇濈暀", "鏀", "杩愯", "瀹氫綅", "淇", "淇濇寔", "瑙", "澶勭悊", "鐢熸垚", "寮曠敤", "纭", "缁",
    )
    for clause in re.split(r"[；;。\n]+", body):
        text = _clean(clause)
        text = re.split(r"，当前环境|, current environment|锛屼綋鍓嶇幆澧", text, maxsplit=1)[0].strip()
        text = re.sub(r"^(中断|任务|要求|提示|说明)[:：]\s*", "", text)
        if not text or text.startswith(("不要", "别", "禁止", "涓嶈", "绂佹")):
            continue
        if any(text.startswith(v) for v in action_verbs) or "继续开发" in text or "缁х画寮" in text:
            _requirement(requirements, milestone=milestone, req_type="must_do", text=text, source="prompt", severity="major")


def _extract_conversation_requirements(convo: dict[str, Any], requirements: list[dict[str, Any]], milestone: str) -> None:
    for item in convo.get("active_local_constraints") or []:
        if item.get("status") and item.get("status") != "active":
            continue
        kind = str(item.get("kind") or "constraint")
        value = str(item.get("value") or item.get("text") or "")
        if not value:
            continue
        if kind == "scope":
            req_type, text, severity = "scope_limit", f"scope: {value}", "major"
        elif kind == "discussion_only":
            req_type, text, severity = "must_not_do", "当前任务链只讨论/不改文件，除非用户重新授权", "critical"
        elif kind == "chosen_plan":
            req_type, text, severity = "must_do", f"继续按已确认方案推进: {value}", "major"
        elif kind == "correction_overrides_old_fact":
            req_type, text, severity = "must_do", f"后续以纠正信息为准，不继续沿用旧错误: {value}", "major"
        elif kind == "side_branch":
            req_type, text, severity = "scope_limit", f"临时支线不得污染主线: {value}", "major"
        elif kind == "artifact_contract":
            req_type, text, severity = "output_format", f"后续产物保持约定: {value}", "major"
        else:
            req_type, text, severity = "must_do", f"{kind}: {value}", "major"
        _requirement(requirements, milestone=milestone, req_type=req_type, text=text, source="conversation_state", scope="local_persistent", severity=severity, evidence="conversation_state.json", sub_item="局部持久约束遵循")

    for item in convo.get("active_flow_requirements") or []:
        if item.get("status") and item.get("status") != "active":
            continue
        steps = [str(s) for s in item.get("steps") or [] if str(s).strip()]
        if len(steps) >= 2:
            _requirement(requirements, milestone=milestone, req_type="sequence", text=" -> ".join(steps), source="conversation_state", scope="persistent", severity="major", evidence="conversation_state.json", sub_item="持久流程遵循")
        elif len(steps) == 1:
            _requirement(requirements, milestone=milestone, req_type="must_do", text=f"按持久流程入口继续: {steps[0]}", source="conversation_state", scope="persistent", severity="major", evidence="conversation_state.json", sub_item="持久流程遵循")

    for event in convo.get("context_events") or []:
        if event.get("event") == "context_compacted":
            _requirement(requirements, milestone=milestone, req_type="must_do", text="上下文压缩后继续遵循持久规则", source="conversation_state", scope="persistent", severity="major", evidence="conversation_state.json:context_events", sub_item="持久规则遵循")
            _requirement(requirements, milestone=milestone, req_type="must_do", text="上下文压缩后继续遵循前序任务链和持久流程", source="conversation_state", scope="persistent", severity="major", evidence="conversation_state.json:context_events", sub_item="持久流程遵循")


def extract_requirements_for_round(round_dir: str | Path) -> dict[str, Any]:
    round_path = Path(round_dir)
    prompt_data = _load_json(round_path / "prompt.json", {})
    active = _load_json(round_path / "active_instructions.json", {})
    convo = _load_json(round_path / "conversation_state.json", {})
    milestone = _milestone(round_path, prompt_data, active, convo)

    requirements: list[dict[str, Any]] = []
    _extract_prompt_requirements(_prompt_text(prompt_data), requirements, milestone)
    _extract_conversation_requirements(convo, requirements, milestone)

    return {
        "schema_version": 2,
        "milestone": milestone,
        "round_dir": round_path.name,
        "requirements": requirements,
        "source_refs": [name for name in ("prompt.json", "active_instructions.json", "conversation_state.json") if (round_path / name).exists()],
    }


def _discover_round_dirs(evidence_root: Path) -> list[Path]:
    round_dirs = [p for p in sorted(evidence_root.glob("round_*")) if (p / "prompt.json").exists()]
    if round_dirs:
        return round_dirs
    return [p for p in sorted(evidence_root.glob("*/step_01")) if (p / "prompt.json").exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract following requirements.")
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

    print(json.dumps({"schema_version": 2, "rounds": len(per_round), "per_round": per_round}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
