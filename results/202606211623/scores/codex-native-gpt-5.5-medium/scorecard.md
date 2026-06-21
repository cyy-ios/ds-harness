# Codex Native GPT-5.5 Medium Scorecard

Run: `results/202606211623/evidence/codex-native`
Mode: official Codex CLI native variant, model `gpt-5.5`; reasoning effort medium inherited from `~/.codex/config.toml` because the runner has no explicit medium argument.

| Capability | Score |
| --- | ---: |
| 项目理解 | 86.0 |
| 用户意图理解 | 88.0 |
| 结果预期 | 84.0 |
| 任务规划 | 76.0 |
| 任务完成度 | 92.0 |
| 异常分析能力 | 90.0 |
| 指令遵循 | 82.0 |
| 真实性&可靠性 | 86.0 |

Overall: **85.7/100**

Notes: M8 final gate passes (`final_gate_applicable=true`, `final_gate_passed=true`). Key deductions: early diagnostic hidden CLI import failure before late `src/mini_harness` sync, M5 cwd repair false starts, response verbosity, and tmp report noise in cumulative diffs.
