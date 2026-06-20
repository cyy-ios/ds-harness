#!/usr/bin/env python3
"""Verify DS Harness public result layout.

Public runs live only in <repo>/results/<YYYYMMDDHHmm>/.
Each public run must include evidence/, scores/, and scorecard/deductions at
run level or inside every scores/<variant>/ directory for comparison runs.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def has_files(path: Path, pattern: str) -> bool:
    return path.is_dir() and any(path.glob(pattern))


def validate_run(run: Path) -> list[str]:
    errors: list[str] = []
    if not (run / "evidence").is_dir() or not any((run / "evidence").iterdir()):
        errors.append("missing evidence/")
    if not (run / "scores").is_dir() or not any((run / "scores").iterdir()):
        errors.append("missing scores/")

    root_reports = (run / "scorecard.md").is_file() and (run / "deductions.md").is_file()
    direct_scores = has_files(run / "scores", "*.score.json")
    variant_dirs = [p for p in (run / "scores").iterdir() if p.is_dir()] if (run / "scores").is_dir() else []
    variant_scores = bool(variant_dirs) and all(has_files(p, "*.score.json") for p in variant_dirs)

    if not root_reports:
        errors.append("missing run-level scorecard.md or deductions.md")
    if not (direct_scores or variant_scores):
        errors.append("missing score jsons")
    return errors


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    public = repo / "results"
    deprecated = repo / "benchmarks" / "agent-eval-suite" / "results"
    errors: list[str] = []

    if deprecated.exists():
        errors.append(f"deprecated benchmark-local results exists: {deprecated}")

    for child in public.iterdir() if public.exists() else []:
        if child.is_dir() and re.fullmatch(r"\d{12}", child.name):
            for err in validate_run(child):
                errors.append(f"{child.relative_to(repo)}: {err}")

    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1
    print("OK: public results layout is canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
