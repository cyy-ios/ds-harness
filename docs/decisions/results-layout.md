# Results layout decision

Canonical public result root is `<ds-harness>/results/<YYYYMMDDHHmm>/`.

Required public run shape:

```text
results/<timestamp>/
  evidence/<variant>/
  scores/
  scorecard.md
  deductions.md
```

Comparison runs may put reports per variant:

```text
results/<timestamp>/
  evidence/<variant>/
  scores/<variant>/scorecard.md
  scores/<variant>/deductions.md
```

Root cause of the previous split:

- `rubrics/scoring-output.md` said `<ds-harness>/results/{timestamp}/`.
- `orchestrator.md` set CWD to `benchmarks/agent-eval-suite/` and used relative `results/${timestamp}/...` examples.
- Runners accepted any `--out` path and did not reject benchmark-local results.
- Manual scoring later wrote some scores to root `results/`, leaving evidence under benchmark-local `results/`.

Fix:

- Migrated complete public runs into root `results/`.
- Moved incomplete or historical non-public outputs to `internal/archive/`.
- Removed `benchmarks/agent-eval-suite/results/`.
- Updated orchestration docs to run from repo root with `result_root=results/${timestamp}`.
- Added runner guards that refuse `benchmarks/agent-eval-suite/results/`.
- Added `scripts/verify_results_layout.py` as the completion gate.
