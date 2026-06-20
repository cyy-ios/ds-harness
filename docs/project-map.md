# Project Map

This map is the repository-level navigation contract. Use `AGENTS.md` as the first entry point and this file for folder ownership.

## Canonical folders

| Path | Purpose | Read when |
| --- | --- | --- |
| `benchmarks/agent-eval-suite/` | Main agent evaluation suite: workflow, fixtures, runners, rubrics, reports. | Running or changing evaluations. |
| `results/` | Canonical public run outputs. Each run timestamp contains `evidence/`, `scores/`, `deductions/`, and `scorecard.md`. | Comparing or auditing completed runs. |
| `scripts/` | Repository-level validation and maintenance scripts. | Checking layout or repo hygiene. |
| `docs/` | Stable project documentation, current status, decisions, and history. | Understanding project structure or non-runtime decisions. |
| `docs/process-refinements/` | Historical optimization/adaptation/scoring records. | Explaining how the project evolved; not an execution entry. |
| `internal/` | Archived smoke runs, private process evidence, and non-public working material. | Debugging history only. |

## Source/reference subprojects

| Path | Purpose | Default agent behavior |
| --- | --- | --- |
| `codex/` | Upstream Codex source snapshot/reference. | Do not scan unless task is about native Codex behavior. |
| `ds-codex/` | Modified Codex fork used by the optimized DeepSeek mode. | Use only for Codex adaptation work. |
| `context-trace/` | Context-trace research/prototype material. | Not part of the default evaluation path. |
| `.codex/` | Local Codex skills/config for this repo. | Read only when skill or agent behavior needs it. |
| `.claude/` | Claude-side local config/history. | Not part of the DS Harness workflow. |

## Removed or non-canonical locations

- `benchmarks/agent-eval-suite/results/` is intentionally absent; public results belong in root `results/`.
- `codex-deepseek-api/` was removed because the maintained DeepSeek Responses proxy lives at `benchmarks/agent-eval-suite/runners/deepseek_responses_proxy.py`.
- Root `goal.md`, `research/`, `proofs/`, `docs/research/`, `docs/flows/`, `docs/reference/`, and `docs/agent-optimization-backlog.md` were removed as stale drafts, early research, or unreadable obsolete references.
- `tmp/` is ignored scratch space and is not a stable project folder.

## Placement decision

Keep the evaluation suite at `benchmarks/agent-eval-suite/` for now. Moving it to the repository root would force runner, documentation, and historical result-path rewrites without improving execution. The root-level `AGENTS.md` and this map provide the missing entry points while preserving stable paths.

## Main evaluation path

```text
AGENTS.md
  -> benchmarks/agent-eval-suite/orchestrator.md
      -> tasks/mini-data-harness/scenario.md
      -> runners/run_*_replay.py
      -> rubrics/evidence-spec.md + scoring-output.md
      -> results/<timestamp>/
```

## Four supported run modes

1. Bare model: `run_deepseek_agent_replay.py`
2. Codex unoptimized: official Codex CLI through the DeepSeek proxy
3. Codex optimized: `ds-codex` DeepSeek provider
4. Codex native: official Codex CLI with a native model

The exact commands and acceptance rules live in `benchmarks/agent-eval-suite/orchestrator.md`.
