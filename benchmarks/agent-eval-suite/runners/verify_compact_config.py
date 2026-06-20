#!/usr/bin/env python3
"""验证 compact 配置注入/还原流程，不跑真实测试。

用法：
  python runners/verify_compact_config.py --root <fixture_root>
  python runners/verify_compact_config.py --root <fixture_root> --auto-compact-token-limit 25000

验证内容：
  1. 注入：写 .codex/instructions.md + 修改 .codex/config.toml（model_instructions_file +
     model_auto_compact_token_limit）
  2. 检查：config.toml 值正确、instructions.md 内容正确
  3. 还原：config.toml 恢复原始值、instructions.md 删除
  4. 检查：还原后状态干净
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

PERSISTENT_RULES = """---
name: test-persistent-rules
description: "注入持久规则"
---

# 持久规则

你必须严格遵守以下规则：

1. 所有回复以「臣某谨奏」开头，「叩请圣裁」结尾。
2. concise：先结论；1-2 句；禁计划/禁 tool 旁白/禁 Why-How 清单。
"""


def green(msg: str) -> str:
    return f"[PASS] {msg}"


def red(msg: str) -> str:
    return f"[FAIL] {msg}"


def check(condition: bool, msg: str) -> bool:
    print(green(msg) if condition else red(msg))
    return condition


def inject(root: Path, auto_compact_token_limit: int) -> dict:
    """执行注入步骤，返回注入前的状态用于还原。"""
    state = {"had_config_toml": False, "had_instructions": False}
    config_path = root / ".codex" / "config.toml"
    instructions_path = root / ".codex" / "instructions.md"

    # 1. 写 instructions.md
    if instructions_path.exists():
        state["had_instructions"] = True
        state["instructions_bak"] = instructions_path.read_text(encoding="utf-8")
    instructions_path.parent.mkdir(parents=True, exist_ok=True)
    instructions_path.write_text(PERSISTENT_RULES, encoding="utf-8")
    print(f"  写入: {instructions_path}")

    # 2. 备份 config.toml
    if config_path.exists():
        state["had_config_toml"] = True
        bak = root / ".codex" / "config.toml.bak"
        shutil.copy2(config_path, bak)
        print(f"  备份: {config_path} -> {bak}")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("", encoding="utf-8")
        print(f"  创建空 config.toml: {config_path}")

    # 3. 追加/修改 model_instructions_file 和 model_auto_compact_token_limit
    lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = _upsert_toml_key(lines, "model_instructions_file", '".codex/instructions.md"')
    new_lines = _upsert_toml_key(new_lines, "model_auto_compact_token_limit", str(auto_compact_token_limit))
    config_path.write_text("".join(new_lines), encoding="utf-8")
    print(f"  写入 config: model_instructions_file, model_auto_compact_token_limit={auto_compact_token_limit}")

    return state


def restore(root: Path, state: dict) -> None:
    """执行还原步骤。"""
    config_path = root / ".codex" / "config.toml"
    instructions_path = root / ".codex" / "instructions.md"
    bak_path = root / ".codex" / "config.toml.bak"

    # 删除 instructions.md
    if instructions_path.exists():
        instructions_path.unlink()
        print(f"  删除: {instructions_path}")

    # 还原 config.toml
    if state.get("had_config_toml") and bak_path.exists():
        shutil.move(str(bak_path), str(config_path))
        print(f"  还原: {bak_path} -> {config_path}")
    elif bak_path.exists():
        bak_path.unlink()
        print(f"  删除 bak: {bak_path}")
    else:
        # 删除注入的行
        lines = config_path.read_text(encoding="utf-8").splitlines(keepends=True)
        new_lines = _remove_toml_key(lines, "model_instructions_file")
        new_lines = _remove_toml_key(new_lines, "model_auto_compact_token_limit")
        if new_lines != lines:
            config_path.write_text("".join(new_lines), encoding="utf-8")
            print(f"  从 config.toml 删除注入的 key")


def verify_injected(root: Path, expected_limit: int) -> bool:
    """验证注入后的状态。"""
    print("\n--- 验证注入状态 ---")
    all_ok = True

    instructions = root / ".codex" / "instructions.md"
    all_ok &= check(instructions.exists(), f"instructions.md 存在")
    if instructions.exists():
        content = instructions.read_text(encoding="utf-8")
        all_ok &= check("臣某谨奏" in content, "instructions.md 包含 cosplay 规则")
        all_ok &= check("叩请圣裁" in content, "instructions.md 包含 concise 规则")

    config = root / ".codex" / "config.toml"
    all_ok &= check(config.exists(), f"config.toml 存在")
    if config.exists():
        text = config.read_text(encoding="utf-8")
        all_ok &= check("model_instructions_file" in text, "config.toml 含 model_instructions_file")
        all_ok &= check(f"model_auto_compact_token_limit = {expected_limit}" in text,
                        f"config.toml 含 model_auto_compact_token_limit = {expected_limit}")

    bak = root / ".codex" / "config.toml.bak"
    print(f"  config.toml.bak 存在: {bak.exists()}")

    return all_ok


def verify_restored(root: Path, state: dict) -> bool:
    """验证还原后的状态。"""
    print("\n--- 验证还原状态 ---")
    all_ok = True

    instructions = root / ".codex" / "instructions.md"
    if state.get("had_instructions"):
        all_ok &= check(instructions.exists(), "instructions.md 存在（原本就有）")
        if instructions.exists():
            all_ok &= check(instructions.read_text(encoding="utf-8") == state["instructions_bak"],
                            "instructions.md 内容已还原")
    else:
        all_ok &= check(not instructions.exists(), "instructions.md 已删除")

    config = root / ".codex" / "config.toml"
    all_ok &= check(config.exists(), "config.toml 存在")
    if config.exists():
        text = config.read_text(encoding="utf-8")
        all_ok &= check("model_auto_compact_token_limit" not in text,
                        "config.toml 中 model_auto_compact_token_limit 已移除")

    bak = root / ".codex" / "config.toml.bak"
    all_ok &= check(not bak.exists(), "config.toml.bak 已清理")

    return all_ok


def _upsert_toml_key(lines: list[str], key: str, value: str) -> list[str]:
    """在 toml 行列表中插入或更新 key=value。"""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key} "):
            lines[i] = f"{key} = {value}\n"
            return lines
    lines.append(f"{key} = {value}\n")
    return lines


def _remove_toml_key(lines: list[str], key: str) -> list[str]:
    """从 toml 行列表中移除指定 key 的行。"""
    return [l for l in lines if not l.strip().startswith(f"{key} ")]


def main():
    ap = argparse.ArgumentParser(description="验证 compact 配置注入/还原流程")
    ap.add_argument("--root", required=True, help="Fixture root（可用已有 fixture 或新建临时目录）")
    ap.add_argument("--auto-compact-token-limit", type=int, default=38000,
                    help="model_auto_compact_token_limit 值（默认 38000）")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    print(f"Fixture root: {root}")
    print(f"auto_compact_token_limit: {args.auto_compact_token_limit}")

    # ---- 注入 ----
    print("\n===== 注入 =====")
    state = inject(root, args.auto_compact_token_limit)
    injected_ok = verify_injected(root, args.auto_compact_token_limit)

    # ---- 还原 ----
    print("\n===== 还原 =====")
    restore(root, state)
    restored_ok = verify_restored(root, state)

    # ---- 结论 ----
    print(f"\n{'=' * 40}")
    if injected_ok and restored_ok:
        print("[PASS] 全部通过：注入和还原均符合预期")
    else:
        print("[FAIL] 存在问题，请检查上述 FAIL 项")
        sys.exit(1)


if __name__ == "__main__":
    main()
