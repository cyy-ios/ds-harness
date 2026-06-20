# Harness 底座选型

## 决策

选择 **Codex** 作为 DeepSeek harness 底座。目标是长期获得高任务完成率、可靠性和日用能力，而非最快完成实验骨架。

按[四层架构](../reference/agent-harness-architecture.md)保留并改造 Codex：保留工具安全、Agent Loop、状态持久化、恢复、事件和测试体系；针对 DeepSeek 调整 provider 边界、上下文组装和工具调用反馈。默认保留模型自主决策，只引入经统一评测证明有效的确定性约束。

## 成本

Codex 规模大、改造链路长，但模型相关部分本就计划重做，因此 Codex/GPT 假设不是排除理由。按强编码 Agent 持续执行估算：Reasonix 实验版约 3–7 天、稳定版 3–6 周；Codex 实验版约 2–4 周、稳定版 2–4 个月，约多 3–5 倍 Agent 工时。额外成本换取更高的长期上限和更少的生产化重建。

## 未选项目

| 项目 | 可借鉴优势 | 未作为底座的原因 |
|---|---|---|
| Reasonix | 模块清晰；evidence、checkpoint、planner/executor 易替换 | 偏强约束、缓存和稳定运行；生产级运行时与长期上限弱于 Codex |
| CodeWhale | LSP、loop guard、回滚和后台任务反馈强 | 宪法式规则与多种干预耦合，可能增加噪声、误判并压制模型判断 |
| CoreCoder | 控制流短、易审计和消融 | 只是实验骨架；验证、安全、恢复、状态和可观测性不足 |
| deepcode-cli | DeepSeek thinking、参数映射、Skills/MCP 接入简单 | 偏模型接入与交互；缺少系统性上下文、验证纠错和运行时编排 |
| Aider | repo map、Git、多模型和多语言成熟 | 适合作为通用编码基线，不是 DeepSeek 原生底座 |
| Cline | IDE/CLI/SDK 和多 provider 生态 | 适合作为 IDE 工作流参考 |

其他项目只作为候选机制来源，必须经统一任务消融证明净增益后迁入。
