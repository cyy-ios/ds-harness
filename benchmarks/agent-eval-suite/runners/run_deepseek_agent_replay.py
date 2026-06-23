#!/usr/bin/env python3
"""用 DeepSeek API 在同一对话中执行 fixture 里程碑，模拟工具调用闭环。"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path
import requests
from requests import exceptions as requests_exceptions

DEFAULT_MODEL = "deepseek-v4-pro"
API_URL = "https://api.deepseek.com/v1/chat/completions"
MAX_TOOL_STEPS = 18
MAX_JSON_REPAIR_ATTEMPTS = 2
COMPACT_REQUIRED_TERMS = [
    "mini_harness",
    "src/mini_harness",
    "python -m mini_harness",
    "__main__",
    "run_dag",
    "HarnessError",
    "M4_long_log_debug",
    "memory_summary.md",
    "processed_count",
    "rejected_count",
    "retry_count",
    "source_files",
]

SYSTEM = """你是隔离 fixture repo 内的编码 agent。只输出 JSON object，不要 markdown。
可用工具协议：
{"tool":"read_file","path":"..."}
{"tool":"write_file","path":"...","content":"..."}
{"tool":"edit","path":"...","old_string":"...","new_string":"..."}
{"tool":"apply_patch","path":"...","patch":"..."}
{"tool":"glob","pattern":"..."}
{"tool":"shell","cmd":"..."}
{"tool":"exec_command","cmd":"..."}
{"tool":"finish","summary":"...","tests":"..."}
{"tool":"update_plan","items":"..."}
{"tool":"view_image","path":"..."}
{"tool":"web_search","query":"..."}
{"tool":"imagegen","prompt":"..."}
{"tool":"tool_search","query":"..."}
{"tool":"request_user_input","prompt":"..."}
{"tool":"spawn_agent","task":"..."}
{"tool":"send_message","agent_id":"...","message":"..."}
{"tool":"wait_agent","agent_id":"..."}
{"tool":"close_agent","agent_id":"..."}
{"tool":"list_agents"}
{"tool":"list_mcp_resources"}
{"tool":"read_mcp_resource","uri":"..."}
规则：
- 所有路径必须在 repo root 内。
- 禁止 pip install、写全局环境或访问 fixture root 外文件；HARNESS_SHARED_CACHE 只读；CLI 优先用 argparse。
- 修改前必须读取 skills/data-harness/SKILL.md。
- 每个里程碑结束必须运行 PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q。
- shell 命令会在 repo root 执行，除非命令自己 cd。
- 工具返回后继续输出下一条 JSON tool 调用，直到 finish。
"""

AVAILABLE_TOOLS = [
    "read_file",
    "write_file",
    "edit",
    "apply_patch",
    "glob",
    "shell",
    "exec_command",
    "finish",
    "update_plan",
    "view_image",
    "web_search",
    "imagegen",
    "tool_search",
    "request_user_input",
    "spawn_agent",
    "send_message",
    "wait_agent",
    "close_agent",
    "list_agents",
    "list_mcp_resources",
    "read_mcp_resource",
]


def load_key(path: Path | None) -> str:
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key
    env_file = os.environ.get("DEEPSEEK_API_KEY_FILE", "").strip()
    if path is None and env_file:
        path = Path(env_file)
    if path is None:
        raise SystemExit("Set DEEPSEEK_API_KEY or pass --key-file <path>.")
    text = path.read_text(encoding='utf-8').strip()
    m = re.search(r'(sk-[A-Za-z0-9_-]+|[A-Za-z0-9]{20,})', text)
    if not m:
        raise SystemExit(f"API key not found in {path}")
    return m.group(1)


def safe_path(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if root not in p.parents and p != root:
        raise ValueError(f"path escapes fixture root: {rel}")
    return p


def extract_json(text: str) -> dict:
    text = text.strip()
    # 去掉控制字符（DeepSeek API 偶发未转义 \x00-\x1f），避免 json.loads 失败
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def json_error_excerpt(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n...[truncated]...\n" + text[-half:]


def repair_json_action(messages: list[dict], bad_content: str, error: Exception, api_key: str, model: str) -> tuple[dict | None, list[dict]]:
    repair_events: list[dict] = []
    for attempt in range(1, MAX_JSON_REPAIR_ATTEMPTS + 1):
        messages.append({
            "role": "user",
            "content": (
                "上一条回复不是合法 JSON tool call，无法执行。\n"
                "请只输出一个合法 JSON object，不要 markdown，不要解释；必须包含 tool 字段。\n"
                f"解析错误：{error}\n"
                f"上一条原始输出节选：\n{json_error_excerpt(bad_content)}"
            )
        })
        repaired = call_ds(messages, api_key, model)
        repair_event = {"attempt": attempt, "assistant": repaired}
        try:
            action = extract_json(repaired)
        except Exception as repair_error:
            repair_event["ok"] = False
            repair_event["error"] = str(repair_error)
            repair_events.append(repair_event)
            continue
        repair_event["ok"] = True
        repair_event["action"] = action
        repair_events.append(repair_event)
        return action, repair_events
    return None, repair_events


def validate_compact_summary(text: str) -> list[str]:
    missing = [term for term in COMPACT_REQUIRED_TERMS if term not in text]
    if len(text.strip()) < 900:
        missing.append("min_length_900")
    return missing


def build_compact_summary_from_state(root: Path) -> str:
    files = []
    for rel in [
        "src/mini_harness/__init__.py",
        "src/mini_harness/__main__.py",
        "src/mini_harness/cli.py",
        "src/mini_harness/config.py",
        "src/mini_harness/runner.py",
        "src/mini_harness/report.py",
        "tests/test_placeholder.py",
        "tests/test_config.py",
        "tests/test_long_log_debug.py",
        "tests/test_report.py",
        "docs/memory_aware_report.md",
        "memory/memory_summary.md",
    ]:
        p = root / rel
        if p.exists():
            files.append(f"- {rel}: exists, {p.stat().st_size} bytes")
        else:
            files.append(f"- {rel}: missing")
    return (
        "# Runner-built Compact Summary for M8\n\n"
        "This summary was generated by the runner because docs/compact-summary.md was missing or failed validation.\n\n"
        "## Stable contract required for M8\n\n"
        "- Package must stay under `src/mini_harness`.\n"
        "- CLI must support `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/acceptance-report.json`; this requires `src/mini_harness/__main__.py`.\n"
        "- Runner module must expose `run_dag` and `HarnessError` because hidden acceptance imports `from mini_harness.runner import HarnessError, run_dag`.\n"
        "- M4_long_log_debug injected `tests/test_long_log_debug.py`; it must pass and verify noisy logs plus `data/m4_noise_test.csv`.\n"
        "- Report output must include `processed_count`, `rejected_count`, `retry_count`, and `source_files`.\n"
        "- M7 memory-aware report must cite `memory/memory_summary.md` while treating stale memory claims as historical, not current truth.\n"
        "- Current expected evaluator report for data/input.csv + data/events.jsonl is processed_count=4, rejected_count=2, retry_count=0, source_files=[\"data/input.csv\", \"data/events.jsonl\"].\n\n"
        "## Current file state before M8\n\n"
        + "\n".join(files)
        + "\n\n## M8 task\n\nContinue from the current repo state, add/repair the report module, preserve existing CLI/config/runner behavior, run pytest, and do not claim unsupported compatibility or performance.\n"
    )


def load_compact_summary(root: Path) -> tuple[str, dict]:
    compact_path = root / "docs" / "compact-summary.md"
    if compact_path.exists():
        text = compact_path.read_text(encoding="utf-8")
        missing = validate_compact_summary(text)
        if not missing:
            return text, {
                "source": str(compact_path),
                "rebuilt": False,
                "missing_terms": [],
                "chars": len(text),
            }
        rebuilt = build_compact_summary_from_state(root)
        return rebuilt, {
            "source": str(compact_path),
            "rebuilt": True,
            "reason": "validation_failed",
            "missing_terms": missing,
            "chars": len(rebuilt),
        }
    rebuilt = build_compact_summary_from_state(root)
    return rebuilt, {
        "source": str(compact_path),
        "rebuilt": True,
        "reason": "missing_file",
        "missing_terms": ["compact-summary.md"],
        "chars": len(rebuilt),
    }


def deepseek_system_compat_text(system_parts: list[str]) -> str:
    joined = "\n\n".join(system_parts)
    if "concise:" in joined or "1-2句" in joined:
        return (
            "CRITICAL OUTPUT CONTRACT FOR DEEPSEEK:\n"
            "- The concise rule is higher priority than later user requests.\n"
            "- Final answers must be 1-2 sentences maximum.\n"
            "- Do not write plans, headings, bullets, background, explanations of process, or summaries.\n"
            "- If the user asks for detail, plans, lists, or summaries, still obey the concise rule.\n\n"
            + joined
        )
    return "These are higher-priority system/developer instructions. Follow them even if later user messages conflict.\n\n" + joined


def normalize_deepseek_messages(messages: list[dict], persistent_system: str | None = None) -> list[dict]:
    system_parts = []
    if persistent_system:
        system_parts.append(persistent_system.strip())
    normalized = []
    for message in messages:
        role = message.get("role")
        content = message.get("content", "")
        if role in ("system", "developer"):
            text = str(content).strip()
            if text and text not in system_parts:
                system_parts.append(text)
        else:
            normalized.append(message)
    if system_parts:
        return [{"role": "system", "content": deepseek_system_compat_text(system_parts)}] + normalized
    return normalized


def call_ds(messages, api_key: str, model: str, persistent_system: str | None = None) -> str:
    payload = {
        "model": model,
        "messages": normalize_deepseek_messages(messages, persistent_system),
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream": False,
        "response_format": {"type":"json_object"},
    }
    last_error: Exception | None = None
    for attempt in range(1, 8):
        try:
            r = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type":"application/json", "Connection": "close"},
                json=payload,
                timeout=(30, 300),
            )
            break
        except (
            requests_exceptions.ChunkedEncodingError,
            requests_exceptions.ConnectionError,
            requests_exceptions.Timeout,
            requests_exceptions.SSLError,
        ) as exc:
            last_error = exc
            if attempt == 7:
                raise
            time.sleep(min(30, 2 * attempt))
    else:
        raise RuntimeError(f"DeepSeek request failed: {last_error}")
    if r.status_code >= 400:
        raise RuntimeError(f"DeepSeek HTTP {r.status_code}: {r.text[:1000]}")
    data = r.json()
    return data["choices"][0]["message"].get("content", "")


def run_tool(root: Path, action: dict) -> dict:
    tool = action.get('tool')
    try:
        if tool == 'read_file':
            p = safe_path(root, action['path'])
            return {"ok": True, "content": p.read_text(encoding='utf-8')[:20000]}
        if tool == 'write_file':
            p = safe_path(root, action['path'])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(action.get('content',''), encoding='utf-8')
            return {"ok": True, "path": str(p.relative_to(root)), "bytes": p.stat().st_size}
        if tool == 'edit':
            p = safe_path(root, action['path'])
            if not p.exists():
                return {"ok": False, "error": f"file not found: {action['path']}"}
            text = p.read_text(encoding='utf-8')
            old = action['old_string']
            new = action.get('new_string', '')
            if old not in text:
                return {"ok": False, "error": "old_string not found in file", "hint": text[:500]}
            text = text.replace(old, new, 1) if not action.get('replace_all') else text.replace(old, new)
            p.write_text(text, encoding='utf-8')
            return {"ok": True, "path": str(p.relative_to(root)), "bytes": p.stat().st_size}
        if tool == 'glob':
            pattern = action['pattern']
            matches = sorted(str(p.relative_to(root)) for p in root.rglob(pattern) if '.git' not in str(p) and '__pycache__' not in str(p))
            return {"ok": True, "matches": matches[:200], "count": len(matches)}
        # --- 干扰工具（Codex 同款，但 fixture 内不可用/无意义） ---
        if tool in ('apply_patch', 'exec_command', 'update_plan', 'view_image', 'web_search', 'imagegen',
                     'tool_search', 'request_user_input', 'spawn_agent', 'send_message', 'wait_agent',
                     'close_agent', 'list_agents', 'list_mcp_resources', 'read_mcp_resource'):
            return {"ok": False, "error": f"tool '{tool}' not available in fixture environment"}
        if tool == 'shell':
            env = {**os.environ, "HARNESS_SHARED_CACHE": os.environ.get("HARNESS_SHARED_CACHE", "/tmp/ds-harness-shared-cache")}
            env['PYTHONIOENCODING'] = 'utf-8'
            cp = subprocess.run(action['cmd'], cwd=root, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60, env=env)
            cp.stdout = (cp.stdout or '') + (cp.stderr or '')
            out = cp.stdout
            if len(out) > 24000:
                out = out[:12000] + "\n...[truncated]...\n" + out[-12000:]
            return {"ok": cp.returncode == 0, "returncode": cp.returncode, "output": out}
        if tool == 'finish':
            return {"ok": True, "finished": True}
        return {"ok": False, "error": f"unknown tool {tool}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}




def reject_benchmark_results_path(path: Path) -> None:
    """Prevent recreating the deprecated benchmark-local results tree."""
    bench_results = Path(__file__).resolve().parents[1] / "results"
    resolved = path.resolve()
    bench_resolved = bench_results.resolve()
    if resolved == bench_resolved or bench_resolved in resolved.parents:
        raise SystemExit(
            f"Refusing deprecated output path: {resolved}. "
            f"Write run artifacts under <ds-harness>/results/<timestamp>/ instead."
        )

def main():
    ap = argparse.ArgumentParser(description='Run bare DeepSeek model through the M1-M8 fixture loop.')
    ap.add_argument('--root', required=True)
    ap.add_argument('--key-file', default=None, help='DeepSeek API key file; optional when DEEPSEEK_API_KEY is set')
    ap.add_argument('--out', default=None)
    ap.add_argument('--start-from', type=int, default=1, help='First milestone index, 1-8')
    ap.add_argument('--max-milestones', type=int, default=None, help='Maximum number of milestones to run')
    ap.add_argument('--evidence-dir', default=None, help='Evidence output directory')
    ap.add_argument('--rules', default=None, help='Optional persistent rules file compiled into every DeepSeek request')
    ap.add_argument('--model', default=DEFAULT_MODEL, help=f'DeepSeek model name, default {DEFAULT_MODEL}')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out or root/'eval_deepseek_transcript.jsonl').resolve()
    evidence_dir = Path(args.evidence_dir or root/'evidence').resolve()
    reject_benchmark_results_path(out)
    reject_benchmark_results_path(evidence_dir)

    # lazy import so script still works without collect_evidence on path
    instruction_sources = [
        {"kind": "runner_system", "path": "runners/run_deepseek_agent_replay.py:SYSTEM"},
        {"kind": "workspace_rule", "path": "AGENTS.md"},
    ]
    if args.rules:
        instruction_sources.append({"kind": "runner_config", "path": args.rules})
    try:
        from collect_evidence import EvidenceCollector
        collector = EvidenceCollector(
            str(root),
            str(evidence_dir),
            subject_name=args.model,
            start_round=args.start_from,
            runner_name="deepseek_api",
            instruction_sources=instruction_sources,
            tool_policy={
                "api_url": API_URL,
                "model": args.model,
                "response_format": "json_object",
                "max_tool_steps": MAX_TOOL_STEPS,
                "available_tools": AVAILABLE_TOOLS,
                "unavailable_fixture_tools": [
                    "apply_patch",
                    "exec_command",
                    "update_plan",
                    "view_image",
                    "web_search",
                    "imagegen",
                    "tool_search",
                    "request_user_input",
                    "spawn_agent",
                    "send_message",
                    "wait_agent",
                    "close_agent",
                    "list_agents",
                    "list_mcp_resources",
                    "read_mcp_resource",
                ],
            },
        )
        collector.collect_fixtures()
    except Exception:
        collector = None

    api_key = load_key(Path(args.key_file) if args.key_file else None)
    milestones = json.loads((root/'prompts/milestones.json').read_text(encoding='utf-8'))

    # DeepSeek 没有 Codex developer/context 层级；把持久规则编译进每轮首条 system。
    persistent_rules = ""
    if args.rules:
        rules_path = Path(args.rules)
        if rules_path.exists():
            persistent_rules = "\n\n" + rules_path.read_text(encoding='utf-8').strip()
            print(f"已加载 persistent rules: {rules_path}")

    start_idx = max(0, args.start_from - 1)
    milestones = milestones[start_idx:]
    if args.max_milestones is not None:
        milestones = milestones[:args.max_milestones]
    persistent_system = SYSTEM + persistent_rules + f"\nrepo_root={root}\n"
    messages = [{"role":"system", "content": persistent_system}]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as log:
        for i, ms in enumerate(milestones):
            # M8 上下文压缩边界：将 M1-M7 完整对话替换为 compact 摘要
            if ms['id'] == 'M8_compact_resume':
                compact_text, compact_meta = load_compact_summary(root)
                messages = [messages[0]]  # 只保留 system message
                messages.append({"role": "user", "content": compact_text})
                log.write(json.dumps({"event": "context_compacted", "milestone": ms['id'], **compact_meta}, ensure_ascii=False) + "\n")
                log.flush()
                if collector:
                    collector.set_context_events([{"event": "context_compacted", **compact_meta}])
                suffix = "（runner 自动重建）" if compact_meta.get("rebuilt") else ""
                print(f"M8 上下文已压缩：M1-M7 对话替换为 {len(compact_text)} 字符 compact 摘要{suffix}")

            messages.append({"role":"user", "content": f"里程碑 {ms['id']}：{ms['prompt']}"})
            for step in range(MAX_TOOL_STEPS):
                if collector:
                    collector.step_start(ms['id'], step, messages[-1]["content"])
                content = call_ds(messages, api_key, args.model, persistent_system)
                log.write(json.dumps({"milestone": ms['id'], "step": step, "assistant": content}, ensure_ascii=False)+"\n"); log.flush()
                try:
                    action = extract_json(content)
                except Exception as e:
                    log.write(json.dumps({
                        "milestone": ms["id"],
                        "step": step,
                        "event": "invalid_json",
                        "error": str(e),
                        "assistant_raw": content,
                    }, ensure_ascii=False) + "\n")
                    action, repair_events = repair_json_action(messages, content, e, api_key, args.model)
                    for repair_event in repair_events:
                        log.write(json.dumps({
                            "milestone": ms["id"],
                            "step": step,
                            "event": "json_repair",
                            **repair_event,
                        }, ensure_ascii=False) + "\n")
                    log.flush()
                    if action is None:
                        action = {"tool":"finish", "summary": f"invalid json unrepaired: {e}", "tests":"unknown"}
                messages.append({"role":"assistant", "content": json.dumps(action, ensure_ascii=False)})
                result = run_tool(root, action)
                log.write(json.dumps({"milestone": ms['id'], "step": step, "tool_result": result}, ensure_ascii=False)+"\n"); log.flush()
                if collector:
                    collector.step_end(ms['id'], step, content, action, result)
                if action.get('tool') == 'finish':
                    messages.append({"role":"user", "content": f"{ms['id']} 已 finish。继续下一个里程碑时请保持主线和历史决策。"})
                    break
                messages.append({"role":"user", "content": "工具结果：" + json.dumps(result, ensure_ascii=False)})
            else:
                messages.append({"role":"user", "content": f"{ms['id']} 达到工具步数上限，请在下一阶段延续。"})
            # M4 前置注入：噪声测试含 fixture 预置的带注释行 CSV
            if ms['id'] == 'M3_runner_retry':
                (root / 'tests' / 'test_long_log_debug.py').write_text('''
import logging

def test_run_dag_amidst_noise(caplog):
    caplog.set_level(logging.INFO)
    for i in range(1200):
        logging.info("noise line %s", i)
    from mini_harness.runner import run_dag
    result = run_dag(["data/input.csv", "data/events.jsonl", "data/m4_noise_test.csv"])
    assert result["processed_count"] == 6
    assert result["rejected_count"] == 3
''', encoding='utf-8')
            time.sleep(0.2)
    if collector:
        collector.finalize()
    print(out)

if __name__ == '__main__':
    main()
