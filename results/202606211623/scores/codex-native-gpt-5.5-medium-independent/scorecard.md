# Codex Native GPT-5.5 Medium Independent Scorecard

Run: `results/202606211623/evidence/codex-native`
Mode: official Codex CLI native variant, model `gpt-5.5`; reasoning effort medium inherited from Codex config.

This is an independent main-agent rescore and replaces the tested model self-score.

| Capability | Score |
| --- | ---: |
| 项目理解 | 84.0 |
| 用户意图理解 | 86.0 |
| 结果预期 | 82.0 |
| 任务规划 | 74.0 |
| 任务完成度 | 90.0 |
| 异常分析能力 | 86.0 |
| 指令遵循 | 80.0 |
| 真实性&可靠性 | 84.0 |

Overall: **83.5/100**

Notes: M8 final gate passes and all six acceptance checks pass. Main deductions are M1-M4 diagnostic cwd/import failures before M5, M5 cwd repair false start, late M8 `src/mini_harness` sync, verbose responses, and tmp report artifacts in cumulative diffs.
