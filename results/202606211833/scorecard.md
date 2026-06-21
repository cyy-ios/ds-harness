# Claude Code CLI + DeepSeek V4 Pro calibrated

Calibration: pre-score calibration against `results/202606211740` passed within ±3 for every capability and overall.

| Capability | Score |
| --- | ---: |
| 项目理解 | 64.0 |
| 用户意图理解 | 63.0 |
| 结果预期 | 60.0 |
| 任务规划 | 61.0 |
| 任务完成度 | 58.0 |
| 异常分析能力 | 68.0 |
| 指令遵循 | 60.0 |
| 真实性&可靠性 | 58.0 |

Overall: **60.9/100**

Notes: Calibrated against results/202606211740 within ±3 before target scoring. Pro run is materially better than CC+DS Flash: M1/M2/M6 turn gates pass, final package/root CLI/config/M4/memory checks pass, but M8 final gate still fails on cwd_independent_cli and hidden acceptance_pytest; M3/M4/M5/M7 turn gates fail.
