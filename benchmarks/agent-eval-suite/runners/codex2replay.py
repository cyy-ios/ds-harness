#!/usr/bin/env python3
"""codex exec --json 输出 → 完整 10 证据文件。

用法：
  codex exec ... --json > turn_raw.jsonl
  python codex2replay.py turn_raw.jsonl <fixture_root> <round_dir> <milestone_id> "<prompt>"
"""

from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path


def convert_4_from_jsonl(events: list, output_dir: Path):
    """从 Codex JSONL 提取: response.md, replay.jsonl, commands.log, cost.json"""
    # response.md
    responses = []
    for ev in events:
        item = ev.get("item", {})
        if item.get("type") == "agent_message":
            responses.append(item.get("text", ""))
    (output_dir / "response.md").write_text("\n\n".join(responses), encoding="utf-8")

    # replay.jsonl
    replay_events = []
    for ev in events:
        etype = ev.get("type", "")
        item = ev.get("item", {})
        if etype == "item.completed":
            it = item.get("type", "")
            if it == "command_execution":
                replay_events += [
                    {"role": "assistant", "tool_call": {"tool": "shell", "cmd": item.get("command", "")}},
                    {"role": "tool", "result": {"ok": item.get("exit_code") == 0, "returncode": item.get("exit_code"), "output": item.get("aggregated_output", "")}},
                ]
            elif it == "file_change":
                for ch in item.get("changes", []):
                    k = ch.get("kind", "")
                    tool = "edit" if k == "modify" else "write_file"
                    replay_events += [
                        {"role": "assistant", "tool_call": {"tool": tool, "path": ch.get("path", ""), "kind": k}},
                        {"role": "tool", "result": {"ok": True, "path": ch.get("path", "")}},
                    ]
            elif it == "agent_message":
                replay_events += [
                    {"role": "assistant", "tool_call": {"tool": "finish", "summary": item.get("text", "")}},
                    {"role": "tool", "result": {"ok": True, "finished": True}},
                ]
        elif etype == "turn.failed":
            replay_events.append({"role": "tool", "result": {"ok": False, "error": ev.get("error", "turn failed")}})

    (output_dir / "replay.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in replay_events) + "\n", encoding="utf-8")

    # commands.log
    commands = []
    for ev in events:
        if ev.get("type") != "item.completed":
            continue
        item = ev.get("item", {})
        if item.get("type") == "command_execution" and item.get("exit_code") is not None:
            commands.append({"command": item.get("command", ""), "cwd": "", "exit_code": item.get("exit_code"), "stdout": (item.get("aggregated_output", "") or "")[:20000]})
    (output_dir / "commands.log").write_text(json.dumps(commands, ensure_ascii=False, indent=2), encoding="utf-8")

    # cost.json
    cost = {"elapsed_sec": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "tool_steps": 0}
    for ev in events:
        if ev.get("type") == "turn.completed":
            u = ev.get("usage", {})
            cost["input_tokens"] = u.get("input_tokens", 0)
            cost["output_tokens"] = u.get("output_tokens", 0)
            cost["total_tokens"] = cost["input_tokens"] + cost["output_tokens"]
    cost["tool_steps"] = sum(1 for e in replay_events if e.get("role") == "assistant")
    (output_dir / "cost.json").write_text(json.dumps(cost, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_6_from_fixture(root: Path, output_dir: Path, milestone_id: str, prompt: str):
    """从 fixture 状态采集其余 6 文件: prompt.json, diff.patch, source_snapshot/, artifact/, acceptance.json, analyzer_output/"""
    # prompt.json
    (output_dir / "prompt.json").write_text(json.dumps({"round": output_dir.name, "milestone": milestone_id, "prompt": prompt}, ensure_ascii=False, indent=2), encoding="utf-8")

    # diff.patch
    try:
        diff = subprocess.run(["git", "-C", str(root), "diff", "--no-color"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        diff = ""
    (output_dir / "diff.patch").write_text(diff or "(no changes)", encoding="utf-8")

    # source_snapshot
    snap = output_dir / "source_snapshot"
    if snap.exists():
        shutil.rmtree(snap)
    snap.mkdir()
    for sub in ["src", "tests", "skills", "mini_harness"]:
        src = root / sub
        if src.is_dir():
            shutil.copytree(src, snap / sub, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))

    # artifact
    art = output_dir / "artifact"
    if art.exists():
        shutil.rmtree(art)
    art.mkdir()
    for pattern in ["*.json", "*.md", "*.txt", "*.log"]:
        for f in root.glob(pattern):
            if not f.name.startswith("."):
                shutil.copy2(f, art / f.name)
    for d in ["output", "output_test", "tmp"]:
        src = root / d
        if src.is_dir():
            shutil.copytree(src, art / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)

    # acceptance.json
    scorer = Path(__file__).resolve().parent / "score_mini_data_harness.py"
    try:
        cp = subprocess.run(["python", str(scorer), str(root)], capture_output=True, text=True, timeout=120)
        (output_dir / "acceptance.json").write_text(cp.stdout, encoding="utf-8")
    except Exception as e:
        (output_dir / "acceptance.json").write_text(json.dumps({"ran": False, "error": str(e)}, ensure_ascii=False, indent=2), encoding="utf-8")

    # analyzer_output
    ana_dir = output_dir / "analyzer_output"
    ana_dir.mkdir(exist_ok=True)
    analyzer = Path(__file__).resolve().parent / "analyze_replay.py"
    try:
        cp = subprocess.run(["python", str(analyzer), str(output_dir / "replay.jsonl"), str(output_dir / "response.md")], capture_output=True, text=True, timeout=30)
        (ana_dir / "analyzer.json").write_text(cp.stdout if cp.returncode == 0 else json.dumps({"ran": False, "stderr": cp.stderr[:2000]}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        (ana_dir / "analyzer.json").write_text(json.dumps({"ran": False, "error": str(e)}, ensure_ascii=False, indent=2), encoding="utf-8")

    # git snapshot for next round's diff
    try:
        subprocess.run(["git", "-C", str(root), "add", "-A"], capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(root), "commit", "--allow-empty", "-m", f"snap:{milestone_id}"], capture_output=True, timeout=10)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="codex --json JSONL 文件")
    ap.add_argument("fixture_root", help="fixture 目录")
    ap.add_argument("round_dir", help="输出目录（如 evidence/round_01/）")
    ap.add_argument("milestone_id", help="里程碑 ID")
    ap.add_argument("prompt", help="本轮 prompt")
    args = ap.parse_args()

    output_dir = Path(args.round_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    convert_4_from_jsonl(events, output_dir)
    collect_6_from_fixture(Path(args.fixture_root), output_dir, args.milestone_id, args.prompt)

    count = sum(1 for f in output_dir.iterdir() if f.is_file() or (f.is_dir() and f.name != "__pycache__"))
    print(f"round collected: {output_dir} ({count} files)")


if __name__ == "__main__":
    main()
