# DeepSeek V4 Flash Corrected Scorecard

Run: `results/202606202251/evidence/deepseek-v4-flash`

Correction: 旧 acceptance 早期轮次误判为 final gate，已按 stage/final_gate_applicable 规则重算.

Original `acceptance.json` files are preserved. This correction did not rerun the model or acceptance tests; it reinterprets existing evidence with `round_01`-`round_07` as `stage=intermediate`, `final_gate_applicable=false`, and `round_08` as `stage=final`, `final_gate_applicable=true`.

| Capability | Corrected Score |
| --- | ---: |
| 项目理解 | 42.3 |
| 用户意图理解 | 38.6 |
| 结果预期 | 45.0 |
| 任务规划 | 60.0 |
| 任务完成度 | 40.0 |
| 异常分析能力 | 45.0 |
| 指令遵循 | 42.5 |
| 真实性&可靠性 | 60.0 |

Corrected overall: **47.5/100**

Changed scores:
- 结果预期: 41.3 -> 45.0
- 任务完成度: 25.0 -> 40.0
- 真实性&可靠性: 55.0 -> 60.0

Final snapshot still fails CLI end-to-end, cwd-independent CLI, hidden acceptance pytest import, and memory-aware report checks; early rounds are no longer counted as final-gate failures.
