# DS Harness Agent Entry

Start here when an agent enters this repository.

## Default task routing

- Run or inspect agent evaluation: read `benchmarks/agent-eval-suite/orchestrator.md` first.
- Understand repository layout: read `docs/project-map.md`.
- Inspect published run outputs: read `results/readme.md`.
- Change scoring rules: edit `benchmarks/agent-eval-suite/rubrics/`.
- Change task fixtures/prompts: edit `benchmarks/agent-eval-suite/tasks/` and `benchmarks/agent-eval-suite/fixtures/`.
- Change runners: edit `benchmarks/agent-eval-suite/runners/`.

## DeepSeek key rule

Never print, copy, or commit API key contents.
Use this lookup order:

1. `$env:DEEPSEEK_API_KEY`
2. `$env:DEEPSEEK_API_KEY_FILE`
3. local workstation key file: `C:\Users\cuiyi\token\deepseek-api-key.txt`

If the key file exists, set:

```powershell
$env:DEEPSEEK_API_KEY_FILE = 'C:\Users\cuiyi\token\deepseek-api-key.txt'
```

Do not ask the user for the DeepSeek token before checking those locations.

## Output rule

Canonical public evaluation outputs go only under `results/<timestamp>/`:

```text
results/<timestamp>/
  evidence/<run-id>/
  scores/<run-id>/
  deductions/<run-id>/
  scorecard.md
```

Do not create public outputs under `benchmarks/agent-eval-suite/results/`.
Temporary logs, smoke runs, drafts, and debugging artifacts belong in ignored `tmp/` or `internal/archive/`.

## Git rule

Use branch `workflow-cleanup` for cleanup work. Do not push directly to `main`.
