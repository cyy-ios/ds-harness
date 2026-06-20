# Progress

Updated: 2026-06-20

## Current stable state

- Main evaluation entry: `benchmarks/agent-eval-suite/orchestrator.md`.
- Repository entry for agents: `AGENTS.md`.
- Folder ownership map: `docs/project-map.md`.
- Canonical public outputs: `results/<timestamp>/`.
- Four M1 smoke modes have been launched successfully: bare model, Codex unoptimized, Codex optimized, Codex native.
- Root `results/` layout is guarded by `scripts/verify_results_layout.py`.

## Cleanup state

- Removed stale drafts: root `goal.md`, `research/`, `proofs/`, `docs/research/`, `docs/flows/`, `docs/reference/`, and `docs/agent-optimization-backlog.md`.
- Removed duplicate DeepSeek proxy folder: `codex-deepseek-api/`.
- Kept `docs/process-refinements/` as historical optimization records.

## Rule

Use this file only for current repo status. Long-form history belongs in `docs/process-refinements/`; run evidence belongs in `results/` or `internal/archive/`.
