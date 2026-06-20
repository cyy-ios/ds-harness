# Agent Harness 对比参考

## 评价边界

本文件只比较 agent harness，不比较 UI、生态或模型自身能力。统一层级和边界见 [Codex Agent Harness 四层架构](agent-harness-architecture.md)。“增强模型能力”仅指同模型、同任务、同预算下，提高正确完成率、验证充分性和复杂任务上限；规划、验证或子代理机制的存在不等于产生净增益。

| Harness 层 | 研究内容 |
|---|---|
| 上下文层 | instructions、AGENTS.md、skills、历史、动态环境、消息组装、裁剪与压缩 |
| 工具层 | schema、参数校验、shell/file/MCP、审批、沙箱、结果格式与错误反馈 |
| Agent Loop 层 | 规划、执行、验证、重试、续跑、子代理、预算与终止条件 |
| 状态与运行时层 | thread 状态、持久化、恢复、事件、权限、故障状态、trace 与评测 |

Provider/API、参数、流式响应和工具调用格式属于模型与 harness 的适配边界，分别影响上下文层和工具层，但不单列为第五层。

## 候选策略

- **Codex**：四层完整；以结构化上下文、受控工具、通用 Agent Loop 和可恢复运行时支持模型自主决策，长期维护和产品化基础最好。
- **Reasonix**：Agent Loop 层的 planner/executor、evidence、readiness 和 retry 较强；纠错闭环明确，但错误规划或验证规则可能放大偏差。
- **CodeWhale**：工具层和 Agent Loop 层的 LSP、loop guard、回滚、宪法规则较强；反馈源和干预较多，可能增加噪声并压制模型判断。
- **deepcode-cli**：上下文层和 provider 边界较直接，适合 DeepSeek 接入；状态与运行时层、独立验证和主动恢复较弱。
- **CoreCoder**：最小上下文、工具和循环实现，适合消融实验；状态、安全、恢复和可观测性不足。

当前源码层面的底座适配性判断为 **Codex > Reasonix > CodeWhale > deepcode-cli > CoreCoder**。这不是模型能力排名，最终取舍以统一评测、跨层完整性和维护成本为准。

## Claude Code 样本

现有样本约含 8000 字符 system prompt 和 27 个工具。Claude Code 调用 DeepSeek 时仍沿用 Claude 身份、模型说明、Anthropic 工具格式和提示风格，可能造成身份错乱、上下文污染和适配不良；样本不能代表全部版本。

研究应获取少量版本的多任务、多轮完整 trace，分别观察四层：模型实际收到的上下文、工具 schema/调用/结果、循环与终止过程、token/压缩/权限/状态变化。重点检查第 3、10、20 轮规则保持，并区分 provider 映射、上下文冲突、工具反馈、循环策略和状态恢复缺陷。

## 源码入口

| 项目 | Harness 入口 |
|---|---|
| Codex | `codex/codex-rs/core/src/`、`ext/`、`state/`、`protocol/`、`app-server/` |
| CoreCoder | `other-project/CoreCoder/corecoder/{agent,context,llm,prompt,session}.py` |
| CodeWhale | `other-project/CodeWhale/crates/tui/src/core/engine/`、`crates/{core,protocol,state,execpolicy}/` |
| Reasonix | `other-project/DeepSeek-Reasonix/internal/{agent,evidence,checkpoint,provider,tool}/` |
| deepcode-cli | `other-project/deepcode-cli/src/{session,prompt,settings}.ts`、`src/tools/` |

## 参考版本

候选仓库源码已从工作区移除；后续需要复核时按以下 commit 获取：

| 项目 | Commit |
|---|---|
| CoreCoder | `0cdebf91a614885147908dbd4fc8f89e36e5a1c9` |
| CodeWhale | `8dff2f7525ead210a01347b48f53ae3f20d094ec` |
| Reasonix | `3f75e4e22cdbf515290cfd64549e6680e57aabfa` |
| deepcode-cli | `fc1223b6336222d9350b2d24ee613c145499dbf2` |
