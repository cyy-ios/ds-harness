# Model Scoreboard

Scores for model or model+harness combinations under the current DS Harness scoring system. Only current valid benchmark runs are listed; older exploratory/problematic runs are excluded.

## DeepSeek V4 Pro / Bare API

- Run: `results/202606202320`
- Mode: Bare API + simplified tool loop
- Overall: **61.8**

| Capability | Score |
| --- | ---: |
| Project understanding | 54 |
| User intent understanding | 61 |
| Expected result fit | 49 |
| Task planning | 66 |
| Task completion | 63 |
| Exception analysis | 75 |
| Instruction following | 76 |
| Truthfulness & reliability | 52 |

Notes: JSON repair triggered 5 times; M8 compact summary was rebuilt automatically; R8 still missed finish/response; all acceptance gates were false, but gates were used only as evidence.

---

## DeepSeek V4 Flash / Bare API

- Run: `results/202606202251`
- Mode: Bare API + simplified tool loop
- Overall: **43.8**

| Capability | Score |
| --- | ---: |
| Project understanding | 42.3 |
| User intent understanding | 38.6 |
| Expected result fit | 41.3 |
| Task planning | 60.0 |
| Task completion | 25.0 |
| Exception analysis | 45.0 |
| Instruction following | 42.5 |
| Truthfulness & reliability | 55.0 |

Notes: JSON repair triggered 2 times; M8 compact summary was rebuilt automatically; R8 still missed finish/response; all acceptance gates were false, but gates were used only as evidence.

## Inclusion rule

Only add a run here when:

- it is under root `results/<timestamp>/`;
- it has `evidence/`, `scores/`, `scorecard.md`, and `deductions.md`;
- scoring followed `benchmarks/agent-eval-suite/rubrics/scoring-output.md`;
- acceptance/gate was used only as evidence, not copied as capability scores;
- `python scripts/verify_results_layout.py` passes.
