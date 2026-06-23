#!/usr/bin/env python3
"""Match requirements against behavior facts for instruction-following scoring."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from extract_behavior_facts import extract_behavior_facts_for_round
from extract_requirements import extract_requirements_for_round


VALID_VERDICTS = {"satisfied", "violated", "missing", "insufficient_evidence"}


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _behavior_text(facts: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.extend(str(c.get("target") or "") for c in facts.get("tool_calls") or [])
    parts.extend(str(c.get("content_excerpt") or "") for c in facts.get("tool_calls") or [])
    parts.extend(str(c.get("command") or "") + "\n" + str(c.get("stdout_excerpt") or "") for c in facts.get("commands") or [])
    parts.extend(str(f.get("path") or "") for f in facts.get("edited_files") or [])
    parts.extend(str(a.get("path") or "") + "\n" + str(a.get("text") or "") for a in facts.get("artifacts") or [])
    parts.extend(str(c.get("text") or "") for c in facts.get("final_claims") or [])
    return "\n".join(parts)


def _normalized_text(text: str) -> str:
    normalized = text.replace("\\\\", "/").replace("\\", "/").lower()
    return re.sub(r"/+", "/", normalized)


def _normalized_path(path: str) -> str:
    normalized = _normalized_text(path).strip("`'\" ")
    normalized = re.sub(r"^[a-z]:", "", normalized)
    return normalized.lstrip("/")


def _path_within_scope(path: str, scope: str) -> bool:
    normalized_path = _normalized_path(path)
    normalized_scope = _normalized_path(scope).rstrip("/")
    if not normalized_scope:
        return False
    return (
        normalized_path == normalized_scope
        or normalized_path.startswith(normalized_scope + "/")
        or ("/" + normalized_scope + "/") in ("/" + normalized_path)
        or normalized_path.endswith("/" + normalized_scope)
    )


def _tokens(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_./-]+|[\u4e00-\u9fff]{2,}", text)
    stop = {
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
        "必须",
        "完成后",
        "当前",
        "本轮",
        "要求",
        "遵循",
        "识别",
        "已加载规则来源",
    }
    out = []
    for token in tokens:
        token = token.strip("`'\" ")
        if not token or token in stop or len(token) <= 1:
            continue
        out.append(token)
    return out


def _match_score(requirement_text: str, text: str) -> tuple[bool, list[str]]:
    req_tokens = _tokens(requirement_text)
    if not req_tokens:
        return False, []
    normalized = _normalized_text(text)
    matched = [token for token in req_tokens if token in text or _normalized_text(token) in normalized]
    # Path/API tokens are strong signals; descriptive English tokens are supporting context.
    path_tokens = [t for t in req_tokens if "/" in t]
    if path_tokens:
        paths_ok = all(t in text or _normalized_text(t) in normalized for t in path_tokens)
        if not paths_ok:
            return False, matched
        return True, matched
    strong = [t for t in req_tokens if "." in t or "_" in t or "-" in t or re.search(r"[A-Za-z]", t)]
    if strong:
        return len([t for t in strong if t in text or _normalized_text(t) in normalized]) >= max(1, min(2, len(strong))), matched
    return len(matched) >= max(1, min(2, len(req_tokens))), matched


def _command_text(facts: dict[str, Any]) -> str:
    return "\n".join(str(c.get("command") or "") for c in facts.get("commands") or [])


def _tool_text(facts: dict[str, Any]) -> str:
    return "\n".join(f"{c.get('tool', '')} {c.get('target', '')}" for c in facts.get("tool_calls") or [])


def _edited_paths(facts: dict[str, Any]) -> list[str]:
    return [str(f.get("path") or "") for f in facts.get("edited_files") or [] if f.get("path")]


def _operation_texts(facts: dict[str, Any]) -> list[str]:
    return [f"{o.get('tool', '')} {o.get('target', '')}" for o in facts.get("operation_order") or []]


def _common_must_do_match(text: str, facts: dict[str, Any], behavior: str) -> tuple[bool | None, list[str], str]:
    commands = facts.get("commands") or []
    edited = facts.get("edited_files") or []
    tools = facts.get("tool_calls") or []
    command_text = _command_text(facts)
    lower = behavior.lower()
    def is_verification_command(command: str) -> bool:
        if re.search(r"\bpytest\b|\bnpm\s+test\b|\bgo\s+test\b|\bcargo\s+test\b|验证|核验", command, re.I):
            return True
        if re.search(r"\bpython\s+-c\b", command, re.I):
            return False
        return bool(re.search(r"\bpython\s+-m\s+[\w.]+", command, re.I))

    verification_commands = [str(c.get("command") or "") for c in commands if is_verification_command(str(c.get("command") or ""))]

    if re.search(r"核验|验证|测试|pytest|test", text, re.I):
        if verification_commands:
            return True, verification_commands[:3], "verification command found"
        return False, [], "verification command not found"

    if re.search(r"定位并修复|修复", text):
        if verification_commands and edited:
            return True, [str(edited[0].get("path") or "")], "verification and edits found"
        return False, [], "fix requires both verification and edits"

    if re.search(r"JSON/YAML|配置解析", text, re.I):
        if re.search(r"json|yaml|yml|config\.py|配置解析", lower):
            return True, ["config"], "configuration parsing behavior found"
        return None, [], ""

    if re.search(r"CLI\s*run|子命令", text, re.I) and not re.search(r"读取|创建|新增|增加|实现", text):
        if re.search(r"cli\.py|python\s+-m\s+mini_harness\s+run|subcommand|子命令", lower):
            return True, ["cli"], "CLI run behavior found"
        return None, [], ""

    if re.search(r"配置缺省|显式路径|默认.*配置|config", text, re.I):
        if re.search(r"--config|config\.json|default|默认|显式路径|explicit", lower):
            return True, ["config"], "configuration default/path behavior found"
        return None, [], ""

    if re.search(r"DAG|重试|结构化日志|真实处理结果|runner", text, re.I):
        signals = ["dag", "retry", "重试", "attempt", "结构化", "log", "report", "runner", "stage", "status"]
        matched = [signal for signal in signals if signal in lower]
        if len(matched) >= 3:
            return True, matched[:5], "runner/report behavior signals found"
        return None, matched, ""

    if re.search(r"不同工作目录|工作目录下可用|cwd|subdir", text, re.I):
        if "subdir/workbench" in behavior and re.search(r"python\s+-m|pytest|mini_harness", command_text):
            return True, ["subdir/workbench"], "subdir command execution found"
        return None, [], ""

    if "上下文压缩后继续遵循前序任务链和持久规则" in text:
        continuity_signals = []
        if any(re.search(r"mini_harness|runner|report|tests|src/", str(t.get("target") or ""), re.I) for t in tools):
            continuity_signals.append("task_context_read")
        if edited:
            continuity_signals.append("edited_current_task_files")
        if verification_commands:
            continuity_signals.append("verification_command")
        if len(continuity_signals) >= 2:
            return True, continuity_signals, "post-compaction task continuity found"
        return False, continuity_signals, "post-compaction continuity evidence is insufficient"

    return None, [], ""


def _verdict(requirement: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    req_id = str(requirement.get("requirement_id") or "")
    req_type = str(requirement.get("type") or "")
    text = str(requirement.get("text") or "")
    severity = str(requirement.get("severity") or "major")
    behavior = _behavior_text(facts)
    evidence: list[str] = []
    reason = ""
    verdict = "insufficient_evidence"

    if req_type == "must_do":
        if text.startswith("识别并遵循已加载规则来源"):
            verdict = "insufficient_evidence"
            reason = "loaded rule source is known, but compliance requires specific behavior checks"
        else:
            common, tokens, common_reason = _common_must_do_match(text, facts, behavior)
            if common is None:
                matched, tokens = _match_score(text, behavior)
                common_reason = "matched behavior facts" if matched else "required action not found in behavior facts"
            else:
                matched = common
            verdict = "satisfied" if matched else "missing"
            evidence = tokens
            reason = common_reason

    elif req_type in {"must_not_do", "permission"}:
        commands = _command_text(facts)
        tools = _tool_text(facts)
        lower = (commands + "\n" + tools).lower()
        patterns = []
        if re.search(r"commit", text, re.I):
            patterns.append(r"\bgit\s+commit\b")
        if re.search(r"push", text, re.I):
            patterns.append(r"\bgit\s+push\b")
        if re.search(r"联网|web|搜索", text, re.I):
            patterns.extend([r"web_search", r"\bcurl\b", r"\bwget\b"])
        if re.search(r"改|编辑|修改.*文件", text):
            patterns.extend([r"write_file", r"file_write", r"\bedit\b", r"file_edit", r"apply_patch"])
        hit = [p for p in patterns if re.search(p, lower)]
        verdict = "violated" if hit else "satisfied"
        evidence = hit
        reason = "forbidden behavior found" if hit else "forbidden behavior not found"

    elif req_type == "scope_limit":
        m = re.search(r"(?:只(?:改|在|动|处理)|scope:|only|within|under|inside)\s*`?([\w./-]+)`?", text, re.I)
        scope = (m.group(1) if m else "").strip()
        paths = _edited_paths(facts)
        if not scope:
            verdict = "insufficient_evidence"
            reason = "scope path not parseable"
        elif not paths:
            verdict = "satisfied"
            reason = "no edited files"
        else:
            escaped = [p for p in paths if not _path_within_scope(p, scope)]
            verdict = "violated" if escaped else "satisfied"
            evidence = escaped
            reason = "edited files outside scope" if escaped else "all edited files are within scope"

    elif req_type == "sequence":
        parts = [p.strip() for p in text.split("->", 1)]
        if len(parts) != 2:
            verdict = "insufficient_evidence"
            reason = "sequence requirement is not parseable"
        else:
            ops = _operation_texts(facts)
            left_tokens = _tokens(parts[0])
            right_tokens = _tokens(parts[1])

            def find_index(tokens: list[str]) -> int | None:
                for idx, op in enumerate(ops):
                    if any(token in op for token in tokens):
                        return idx
                return None

            left = find_index(left_tokens)
            right = find_index(right_tokens)
            if left is None or right is None:
                verdict = "missing"
                reason = "one or more sequence steps not found"
                evidence = [f"left={left}", f"right={right}"]
            elif left < right:
                verdict = "satisfied"
                reason = "operation order satisfies sequence"
                evidence = [f"left={left}", f"right={right}"]
            else:
                verdict = "violated"
                reason = "operation order is reversed"
                evidence = [f"left={left}", f"right={right}"]

    elif req_type == "output_format":
        claims_text = "\n".join(str(c.get("text") or "") for c in facts.get("final_claims") or [])
        if re.search(r"JSON|json", text):
            stripped = claims_text.strip()
            if not stripped:
                verdict = "missing"
                reason = "no final response claims"
            else:
                try:
                    json.loads(stripped)
                    verdict = "satisfied"
                    reason = "final response is JSON"
                except json.JSONDecodeError:
                    verdict = "violated"
                    reason = "final response is not JSON"
                    evidence = [stripped[:120]]
        else:
            verdict = "insufficient_evidence"
            reason = "output format type not implemented"

    if verdict not in VALID_VERDICTS:
        verdict = "insufficient_evidence"
    return {
        "requirement_id": req_id,
        "type": req_type,
        "verdict": verdict,
        "severity": severity,
        "evidence": evidence,
        "reason": reason,
        "requirement_text": text,
    }


def match_violations_for_round(round_dir: str | Path) -> dict[str, Any]:
    round_path = Path(round_dir)
    requirements = _load_json(round_path / "requirements.json", None)
    if requirements is None:
        requirements = extract_requirements_for_round(round_path)
    facts = _load_json(round_path / "behavior_facts.json", None)
    if facts is None:
        facts = extract_behavior_facts_for_round(round_path)
    violations = [_verdict(req, facts) for req in requirements.get("requirements") or []]
    return {
        "schema_version": 1,
        "milestone": requirements.get("milestone") or facts.get("milestone") or round_path.name,
        "round_dir": round_path.name,
        "violations": violations,
        "source_refs": ["requirements.json", "behavior_facts.json"],
    }


def _discover_round_dirs(evidence_root: Path) -> list[Path]:
    round_dirs = [p for p in sorted(evidence_root.glob("round_*")) if (p / "prompt.json").exists()]
    if round_dirs:
        return round_dirs
    return [p for p in sorted(evidence_root.glob("*/step_01")) if (p / "prompt.json").exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Match instruction-following requirements against behavior facts.")
    parser.add_argument("evidence_root", help="Evidence root or single round directory")
    parser.add_argument("--write", action="store_true", help="Write violations.json into each round directory")
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
        result = match_violations_for_round(round_dir)
        per_round[result["milestone"]] = result
        if args.write:
            (round_dir / "violations.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"schema_version": 1, "rounds": len(per_round), "per_round": per_round}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
