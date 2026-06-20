# DS Harness Results

Canonical public result root: `results/<YYYYMMDDHHmm>/`.

Each public run directory must contain:
- `evidence/` — collected replay evidence, grouped by variant when needed.
- `scores/` — `*.score.json` files, or per-variant score folders for comparison runs.
- `scorecard.md` and `deductions.md`, or per-variant `scorecard.md` and `deductions.md` under `scores/<variant>/`.

`benchmarks/agent-eval-suite/results/` is deprecated and must not be recreated. Historical incomplete or non-public outputs were moved to `internal/archive/`.

Validate with:

```bash
python scripts/verify_results_layout.py
```
