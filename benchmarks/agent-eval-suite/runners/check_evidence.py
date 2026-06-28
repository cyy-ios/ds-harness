#!/usr/bin/env python3
"""Check the new evidence contract: each round has tool_events.jsonl and result.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _round_dirs(root: Path) -> list[Path]:
    nested = sorted(root.glob("*/step_01"))
    if nested:
        return nested
    return sorted(d for d in root.glob("round_*") if d.is_dir())


def check_evidence(evidence_dir: str) -> tuple[int, int]:
    root = Path(evidence_dir)
    if not root.exists():
        print(f"missing evidence dir: {root}")
        return 0, 1

    rounds = _round_dirs(root)
    if not rounds:
        print("no round directories found")
        return 0, 1

    passed = failed = 0
    for rd in rounds:
        issues: list[str] = []
        tool_events = rd / "tool_events.jsonl"
        result = rd / "result.json"
        if not tool_events.exists():
            issues.append("missing tool_events.jsonl")
        else:
            for line_no, line in enumerate(tool_events.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    issues.append(f"tool_events.jsonl invalid json line {line_no}")
                    break
                if rec.get("kind") not in {"tool_call", "tool_result"}:
                    issues.append(f"tool_events.jsonl invalid kind line {line_no}")
                    break
        if not result.exists():
            issues.append("missing result.json")
        else:
            try:
                data = json.loads(result.read_text(encoding="utf-8"))
                if "response_protocol" not in data:
                    issues.append("result.json missing response_protocol")
            except json.JSONDecodeError:
                issues.append("result.json invalid json")
        if issues:
            print(f"FAIL {rd}: {'; '.join(issues)}")
            failed += 1
        else:
            print(f"OK {rd}")
            passed += 1
    print(f"\npassed {passed}/{passed + failed}")
    return passed, failed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: python {sys.argv[0]} <evidence_dir>")
        sys.exit(1)
    _, failed = check_evidence(sys.argv[1])
    sys.exit(0 if failed == 0 else 1)
