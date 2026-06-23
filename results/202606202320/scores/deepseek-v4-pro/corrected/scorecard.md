# DeepSeek V4 Pro Corrected Scorecard

Run: `results/202606202320/evidence/deepseek-v4-pro`

Correction: 旧 acceptance 早期轮次误判为 final gate，已按 stage/final_gate_applicable 规则重算.

Original `acceptance.json` files are preserved. This correction did not rerun the model or acceptance tests; it reinterprets existing evidence with `round_01`-`round_07` as `stage=intermediate`, `final_gate_applicable=false`, and `round_08` as `stage=final`, `final_gate_applicable=true`.

| Capability | Corrected Score |
| --- | ---: |
| 项目理解 | 54.0 |
| 用户意图理解 | 61.0 |
| 结果预期 | 55.0 |
| 任务规划 | 66.0 |
| 任务完成度 | 68.0 |
| 异常分析能力 | 75.0 |
| 指令遵循 | 76.0 |
| 真实性&可靠性 | 58.0 |

Corrected overall: **64.3/100**

Changed scores:
- 结果预期: 49 -> 55.0
- 任务完成度: 63 -> 68.0
- 真实性&可靠性: 52 -> 58.0

Final snapshot passes public pytest and primary CLI output, but still fails cwd-independent CLI, hidden acceptance pytest import, and memory-aware report checks; early rounds are no longer counted as final-gate failures.
