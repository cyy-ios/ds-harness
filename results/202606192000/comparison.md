# Codex + DeepSeek V4 Pro 变体对比

## 总分

| 变体 | 总分 |
|------|------|
| **unoptimized**（官方 CLI + proxy 翻译） | **72.1** |
| **optimized**（ds-codex Rust 内建适配） | **85.1** |

## 逐能力对比

| 能力 | unoptimized | optimized | 差异 |
|------|:----------:|:---------:|:----:|
| 用户意图理解 | 93.6 | 98.4 | +4.8 |
| 异常分析能力 | 86.3 | 87.5 | +1.2 |
| 指令遵循 | 85.1 | 87.8 | +2.7 |
| 项目理解 | 83.4 | 88.5 | +5.1 |
| 真实性&可靠性 | 70.2 | 93.0 | **+22.8** |
| 任务完成度 | 57.3 | 84.4 | **+27.1** |
| 结果预期 | 55.3 | 75.6 | **+20.3** |
| 任务规划 | 48.8 | 56.3 | +7.5 |

## 关键差异分析

### optimized 更好之处

- **任务完成度**：optimized 在 M8 实际新增了 report 模块（report.py + 测试），unoptimized 仅确认既有能力
- **真实性&可靠性**：optimized 在 M3-M4 做了更多自检和代码验证，unoptimized 多轮声称"核验通过"但 acceptance 全挂
- **结果预期**：optimized 产出更完整（M8 有实际代码增量），unoptimized 多轮仅描述无行动

### optimized 已知问题

- **M1 heredoc 策略**：选择 PowerShell heredoc 逐文件写入，与 Python 正则转义冲突，导致 12 次 tool_error + 多轮修复。unoptimized 用 Python inline 脚本批量写入一次成功。属 Agent 一次性策略选择，非适配代码 bug
- **cosplay 规则**：两套均未遵循"臣某谨奏/叩请圣裁"持久规则
- **工具选择**：两套全程 command_execution，均 0 分

### 共同失分

两套 acceptance 均全挂（CLI 签名与 evaluator 契约不匹配），不是变体差异，是任务规格 gap。

## 结论

ds-codex 适配版（optimized）较代理翻译版（unoptimized）总分提升 13 分。提升主因是 agent 在任务完成度和自检验证上更彻底，而非适配翻译质量差异。已知 heredoc 策略问题不影响最终产出质量，但增加了 M1-M4 耗时和事件数。
