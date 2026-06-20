# Codex Agent Harness 四层架构

## 范围

本文定义本项目分析、改造和评测 Codex 的统一边界。Agent harness 指模型之外、负责把任务组织成可持续执行过程的系统；UI、产品协议和模型本身不属于核心 harness，provider/API 适配是模型与 harness 的边界。

## 四层

| 层 | 职责 | Codex 主要机制 | 本项目关注点 |
|---|---|---|---|
| 1. 上下文层 | 决定模型看到什么，以及指令、历史和动态状态的优先级 | system/developer instructions、AGENTS.md、skills、环境上下文、历史、压缩与恢复 | DeepSeek 身份与能力适配、规则冲突、长程保持、压缩后信息完整性 |
| 2. 工具层 | 把模型意图转换为受约束的外部动作，并把结果反馈给模型 | tool schema、参数解析、shell/file/MCP、审批、沙箱、结果与错误编码 | 工具调用兼容性、参数校验、反馈质量、失败可恢复性 |
| 3. Agent Loop 层 | 编排“推理 → 工具 → 观察 → 再推理”，管理规划、续跑和终止 | turn/session loop、`update_plan`、Goal continuation、重试、终止条件 | 避免空泛分析，推动验证闭环，控制循环、预算和完成判定 |
| 4. 状态与运行时层 | 保存跨轮次事实并保证执行可恢复、可治理、可观测 | thread lifecycle、事件、SQLite 状态、持久化/恢复、token accounting、权限与故障状态 | 长任务恢复、状态一致性、审计、限额、安全和可重复评测 |

四层是职责分解，不是严格的代码依赖栈。一个功能可以横跨多层，但必须标明主层和支撑层。

## 原生功能归属

| 功能 | 主层 | 支撑层 | 实际行为 |
|---|---|---|---|
| `Updated Plan` / `update_plan` | Agent Loop 层 | 工具层、UI 事件展示 | 模型调用工具提交当前 TODO；Core 发出 `PlanUpdate` 事件，客户端渲染。它不依赖 Goal，也不是持久化长任务状态机。 |
| Goal | Agent Loop 层 | 状态与运行时层、工具层、上下文层 | 持久化 objective/status/budget，提供 `create_goal`、`get_goal`、`update_goal`，按生命周期计量并在线程空闲时注入 continuation 继续执行。 |
| Provider/API 适配 | harness 边界 | 上下文层、工具层 | 负责模型请求、流式事件和工具调用格式转换；不应自行承担任务状态机或完成判定。 |
| Skills / AGENTS.md | 上下文层 | 工具层 | 主要向模型注入任务规则和工作流；Skill 本身不是持久化运行时。 |

## Codex 源码入口

| 关注点 | 入口 |
|---|---|
| 上下文与 turn 组装 | `codex/codex-rs/core/src/`、`core/src/session/turn.rs` |
| 工具注册与执行 | `codex/codex-rs/core/src/tools/` |
| `update_plan` | `core/src/tools/handlers/plan.rs`、`tui/src/history_cell/plans.rs` |
| Goal | `codex/codex-rs/ext/goal/`、`state/src/runtime/goals.rs` |
| 状态、事件与恢复 | `codex/codex-rs/state/`、`protocol/`、`app-server/` |

上下文层的完整文件地图、主流程和优化策略见 [Codex 上下文层实现](codex-context-layer.md)。

## 分析规则

1. 先判断问题属于哪一层，再定位 provider、Core、extension、state 或 UI；不要把所有 Codex 行为都归因于 prompt。
2. 跨层改动必须分别验证输入、状态转换、工具反馈和恢复结果。
3. UI 文案不是状态真相；以 Core 事件和持久化状态为准。
4. 候选机制只有在同模型、同任务、同预算下产生可重复净增益，才进入稳定 harness。

## 研究顺序与影响优先级

harness 研究按以下顺序进行：

1. **上下文层**：还原模型每轮实际收到的 instructions、AGENTS.md、skills、环境、历史和压缩结果；优先检查冲突、稀释、遗漏和长程规则衰减。
2. **Agent Loop 层**：检查模型是否从分析进入执行，是否主动验证、根据证据重试，并在真实完成或明确阻塞时终止。
3. **工具层**：检查 schema 是否易于正确调用，成功、失败、审批和截断结果是否给模型足够且低噪声的下一步信息。
4. **状态与运行时层**：检查长任务持久化、恢复、预算、权限、故障状态和事件一致性，确保前三层能力能跨轮次稳定发挥。

对 Agent 智力表现的通常影响为：**上下文层 > Agent Loop 层 ≈ 工具反馈 > 状态与运行时层**。前三层直接决定模型判断、行动和纠错质量；状态与运行时层主要决定这些能力在长任务中的可靠性。每层均以同模型、同任务、同预算的 trace 和消融实验判断，不以功能数量或主观体验判断。
