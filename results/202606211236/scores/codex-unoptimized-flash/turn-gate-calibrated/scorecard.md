# Turn-gate Calibrated Scorecard

Variant: Codex Unoptimized + DeepSeek V4 Flash / Official Codex CLI via proxy
Overall: **79.5/100**

| Capability | Score |
| --- | ---: |
| 项目理解 | 80.0 |
| 用户意图理解 | 78.0 |
| 结果预期 | 78.0 |
| 任务规划 | 68.0 |
| 任务完成度 | 91.0 |
| 异常分析能力 | 72.0 |
| 指令遵循 | 82.0 |
| 真实性&可靠性 | 80.0 |

Turn-gate calibrated rescore v2: per-round states were reconstructed from fresh fixture plus each cumulative diff.patch, avoiding final-state pollution. M1/M2/M3/M5/M6/M7/M8 turn gates pass; M4 fails m4_noise_cli; M8 full final gate passes.

Turn-gate audit: `tmp/turn-audit-unopt-flash-summary.json`.