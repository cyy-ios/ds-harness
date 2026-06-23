# DeepSeek V4 Pro Bare API calibrated

Calibration: pre-score calibration against `results/202606211740` passed within ±3 for every capability and overall.

| Capability | Score |
| --- | ---: |
| 项目理解 | 54.0 |
| 用户意图理解 | 61.0 |
| 结果预期 | 55.0 |
| 任务规划 | 66.0 |
| 任务完成度 | 68.0 |
| 异常分析能力 | 75.0 |
| 指令遵循 | 76.0 |
| 真实性&可靠性 | 58.0 |

Overall: **64.3/100**

Notes: Calibrated against results/202606211740 within ±3. Uses corrected interpretation: early rounds are not final-gate failures; final snapshot still fails cwd-independent CLI, hidden acceptance pytest import, and memory-aware report.
