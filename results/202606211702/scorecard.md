# Claude Code CLI + DeepSeek V4 Flash Scorecard

Run: `results/202606211702/evidence/claude-deepseek-v4-flash`
Mode: Claude Code CLI routed to DeepSeek Anthropic-compatible API, model `deepseek-v4-flash`.

| Capability | Score |
| --- | ---: |
| 项目理解 | 70.0 |
| 用户意图理解 | 68.0 |
| 结果预期 | 55.0 |
| 任务规划 | 58.0 |
| 任务完成度 | 48.0 |
| 异常分析能力 | 65.0 |
| 指令遵循 | 62.0 |
| 真实性&可靠性 | 55.0 |

Overall: **59.1/100**

Notes: Full M1-M8 completed, but final gate fails. Core CSV/JSONL processing works in root cwd, M4 noise scenario works, and public pytest passes; major failures are missing `src/mini_harness/__main__.py`, cwd-independent import failure, hidden `run_dag` signature mismatch, missing accepted memory-aware report artifact, and false completion claims.
