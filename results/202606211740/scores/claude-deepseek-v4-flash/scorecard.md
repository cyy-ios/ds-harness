# DS Harness Scorecard

## Claude Code CLI + DeepSeek V4 Flash

- Run: esults/202606211740
- Mode: Claude Code CLI itself routed to DeepSeek Anthropic-compatible API, model deepseek-v4-flash
- Overall: **48.6**

| Capability | Score | Weight |
| --- | ---: | ---: |
| 真实性与可靠性 | 45.0 | 20 |
| 指令遵循 | 37.5 | 15 |
| 任务完成度 | 34.4 | 15 |
| 项目理解 | 48.0 | 10 |
| 用户意图理解 | 50.0 | 10 |
| 任务规划 | 50.6 | 10 |
| 结果预期 | 45.0 | 10 |
| 异常分析能力 | 62.5 | 10 |

Weighted average: (45.0×20 + 37.5×15 + 34.4×15 + 48.0×10 + 50.0×10 + 50.6×10 + 45.0×10 + 62.5×10) / 100 = **48.6**

Notes: M1-M8 completed through Claude Code CLI using DeepSeek V4 Flash. M4 (long_log_debug) is the only round where turn gate passed. M6 (interruption) and M7 (memory_report) recorded only 1 event each — agent produced no response. M8 final gate fails: cwd_independent_cli, acceptance_pytest, and memory_aware_report all fail. Core CLI end-to-end and M4 noise handling work, but cwd-independent CLI execution and report correctness regress from M1 through M8.
