#!/usr/bin/env python3
"""Convert Codex JSONL into deterministic tool event evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tool_events import from_codex_events, write_jsonl


def read_events(path: Path) -> list[dict]:
    events = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                events.append(item)
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Codex JSONL file")
    parser.add_argument("fixture_root", help="unused; kept for CLI compatibility")
    parser.add_argument("round_dir", help="output directory")
    parser.add_argument("milestone_id", help="milestone id")
    parser.add_argument("prompt", help="unused; kept for CLI compatibility")
    args = parser.parse_args()

    output_dir = Path(args.round_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "tool_events.jsonl", from_codex_events(read_events(Path(args.input)), args.milestone_id))
    print(f"tool events collected: {output_dir / 'tool_events.jsonl'}")


if __name__ == "__main__":
    main()
