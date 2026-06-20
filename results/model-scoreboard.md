# Model Scoreboard

This document records model or model+harness scores under the current DS Harness scoring system.

Only include runs produced after the scoring contract and runner fixes are in place. Older exploratory runs stay in their run folders but are not listed here.

## Current valid scores

| Date | Run | Subject | Mode | Overall | 项目理解 | 用户意图理解 | 结果预期 | 任务规划 | 任务完成度 | 异常分析能力 | 指令遵循 | 真实性&可靠性 | Notes |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-06-20 | `results/202606202251` | DeepSeek V4 Flash | Bare API + simplified tool loop | 43.8 | 42.3 | 38.6 | 41.3 | 60.0 | 25.0 | 45.0 | 42.5 | 55.0 | JSON repair triggered twice; M8 compact summary rebuilt; R8 still lacked finish/response; all acceptance gates false. |

## Inclusion rule

A score may be added here only when:

- the run is under root `results/<timestamp>/`;
- `evidence/`, `scores/`, `scorecard.md`, and `deductions.md` exist;
- scoring followed `benchmarks/agent-eval-suite/rubrics/scoring-output.md`;
- acceptance/gate was used as evidence, not copied as capability scores;
- `python scripts/verify_results_layout.py` passes.
