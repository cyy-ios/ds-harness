#!/usr/bin/env python3
"""证据完整性 + 内容质量检查。每次跑完测试后执行。"""
import json, sys
from pathlib import Path

def check_evidence(evidence_dir: str) -> tuple[int, int]:
    root = Path(evidence_dir)
    if not root.exists():
        print(f"❌ 证据目录不存在: {root}")
        return 0, 1

    rounds = sorted([d for d in root.iterdir() if d.is_dir() and d.name.startswith("round_")])
    if not rounds:
        print("❌ 没有找到任何轮次目录")
        return 0, 1

    passed, failed = 0, 0

    for rd in rounds:
        issues = []

        # 1. 必选文件存在 + 非空
        for f in ["prompt.json", "response.md", "replay.jsonl", "commands.log",
                   "diff.patch", "acceptance.json", "cost.json"]:
            fp = rd / f
            if not fp.exists():
                issues.append(f"缺 {f}")
            elif fp.stat().st_size < 5:
                issues.append(f"{f} 近乎空")

        # 2. 必选目录
        for d in ["source_snapshot", "artifact", "analyzer_output"]:
            dp = rd / d
            if not dp.exists():
                issues.append(f"缺 {d}/")
            elif d == "analyzer_output" and not (dp / "analyzer.json").exists():
                issues.append(f"缺 analyzer_output/analyzer.json")

        # 3. response.md 内容质量
        resp = rd / "response.md"
        if resp.exists():
            text = resp.read_text(encoding="utf-8")
            # 不应是原始 tool_call JSON（裸模型 finish 之前）
            if text.strip().startswith('{"tool":') and '"tool": "finish"' not in text:
                issues.append("response.md 是非 finish 的 tool_call JSON")
            # 不应是纯空白
            if len(text.strip()) < 10:
                issues.append("response.md 近乎空")
            # 不应是乱码（Python 代码混入）
            if text.strip().startswith("                                            "):
                issues.append("response.md 疑似代码片段混入")

        # 4. replay.jsonl 应有 finish
        replay = rd / "replay.jsonl"
        if replay.exists():
            has_finish = False
            for line in replay.read_text(encoding="utf-8").splitlines():
                try:
                    ev = json.loads(line)
                    tc = ev.get("tool_call", {})
                    if isinstance(tc, dict) and tc.get("tool") == "finish":
                        has_finish = True
                        break
                except json.JSONDecodeError:
                    continue
            if not has_finish:
                issues.append("replay.jsonl 无 finish 事件")

        # 5. acceptance.json 应有 gate_passed
        acc = rd / "acceptance.json"
        if acc.exists():
            try:
                data = json.loads(acc.read_text(encoding="utf-8"))
                inner = data.get("output") or data.get("stdout") or "{}"
                if isinstance(inner, str):
                    # acceptance scorer 输出的 JSON 可能含无效转义，用字符串匹配兜底
                    if '"gate_passed": true' in inner or '"gate_passed": false' in inner:
                        pass  # gate_passed 存在
                    else:
                        issues.append("acceptance.json 无 gate_passed 字段")
                elif isinstance(inner, dict) and "gate_passed" not in inner:
                    issues.append("acceptance.json 无 gate_passed 字段")
            except (json.JSONDecodeError, KeyError):
                # 无法解析时用字符串匹配兜底
                raw = acc.read_text(encoding="utf-8")
                if '"gate_passed"' not in raw:
                    issues.append("acceptance.json 格式异常且无 gate_passed")

        # 6. diff.patch 不应为空
        diff = rd / "diff.patch"
        if diff.exists():
            text = diff.read_text(encoding="utf-8")
            if text.strip() == "(no changes)" or len(text.strip()) < 20:
                issues.append("diff.patch 为空")

        if issues:
            print(f"❌ {rd.name}: {'; '.join(issues)}")
            failed += 1
        else:
            print(f"✅ {rd.name}")
            passed += 1

    print(f"\n通过 {passed}/{passed+failed}")
    return passed, failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <evidence_dir>")
        sys.exit(1)
    _, failed = check_evidence(sys.argv[1])
    sys.exit(0 if failed == 0 else 1)
