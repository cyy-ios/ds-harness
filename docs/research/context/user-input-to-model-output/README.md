# 用户输入到模型输出

## 目标

追踪 Codex 最小主链：用户输入 → `run_turn` → `build_prompt` → `client.rs` 请求 → 流式响应处理；确认模型实际收到的消息、顺序及输出返回路径。
 终点不是只看“回复用户的文本”，而是一次 turn 的所有模型输出被 Codex 消费后的结果：assistant 文本、tool call、reasoning/计划片段、错误或完成事件。对这个小任务，最小终点可以定为“模型流式事件如何变成 TUI/exec 可见的 assistant 消息或工具调用”。
 最小链路：用户输入进入 session → run_turn 创建 TurnContext → 追加用户消息/初始上下文到 history → build_prompt 生成最终 Prompt → client.rs 发模型请求 → 接收流式 assistant 文本事件 → turn.rs 聚合并发出 assistant 消息事件 → TUI/exec 展示给用户。

## 暂不研究

压缩、Skills、Goal、恢复、fork、子代理和实时会话分支。

## 产出

- 主链调用图与关键数据结构。
- 最终请求中各消息的来源、角色和顺序。
- 模型流式事件到 Codex 输出事件的映射。
- 已确认问题与待验证假设。

## 当前文档

- [本次会话中的最小上下文链路](session-chain-example.md)
- [Context provenance trace 打点方案](context-provenance-trace.md)
- [实际请求捕获：2026-06-08](actual-capture-2026-06-08.md)
