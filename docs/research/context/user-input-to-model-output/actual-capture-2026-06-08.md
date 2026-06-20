# 实际请求捕获：2026-06-08

## 样本

在 `context-trace` worktree 中创建同一 thread，依次发送本次 Session 的三条用户输入：

1. `如果用户指令不清晰也直接发给模型让模型去理解吗`
2. `hook也起一个追加的作用吗？追加到一起输入给模型？`
3. `他们会塞在一个请求里发给模型？`

Thread ID：`019ea7c4-bf47-73f0-afb9-ce2d2d265b21`。

完整原始记录位于：

```text
C:\项目\ds-harness\internal\context-traces\019ea7c4-bf47-73f0-afb9-ce2d2d265b21.jsonl
C:\项目\ds-harness\internal\context-traces\extracted\
```

每个 turn 的 `extracted/turn-*` 目录包含：

- `history-appends.json`：该轮每次实际追加及调用源码位置。
- `for-prompt.json`：归一化后实际送入采样的 `input[]`。
- `final-prompt.json`：transport 前完整 Prompt，包括 base instructions、input 和 17 个工具 schema。

## Turn 1 实际组装

最终请求包含：

| input 顺序 | role/type | 文本字符数 | 实际来源 |
|---:|---|---:|---|
| 0 | developer | 13,510 | 权限、Skills、Plugins 等聚合上下文 |
| 1 | user | 21,674 | AGENTS.md instructions + environment_context |
| 2 | user | 23 | 第一条用户原文 |
| 3 | developer | 41 | Hook 追加的 concise 规则 |

此外还有：基础 instructions 21,335 字符、工具 schema 17 个。

实际追加调用点：

```text
core/src/session/mod.rs:3072  初始上下文
core/src/session/mod.rs:3244  用户原文
core/src/hook_runtime.rs:594  Hook additional_context（concise）
```

## Turn 2 实际组装

最终 `input[]` 共 8 项：完整保留 Turn 1 的 4 项，再追加：

```text
reasoning
Turn 1 assistant 回复
Turn 2 用户原文
developer: concise Hook 规则
```

基础 instructions 仍为 21,335 字符，工具 schema 仍为 17 个。

## Turn 3 实际组装

最终 `input[]` 共 11 项：完整保留前两轮历史，再追加：

```text
Turn 2 assistant 回复
Turn 3 用户原文
developer: concise Hook 规则
```

基础 instructions 仍为 21,335 字符，工具 schema 仍为 17 个。

## 已确认事实

1. 每次采样确实把基础 instructions、完整累计 history、当前用户输入、Hook 追加规则和全部工具 schema 放进同一个结构化请求。
2. 用户原文先写入 history，随后 Hook 返回的 concise 规则以独立 `developer` 消息追加，而不是合并进用户文本。
3. 后续轮次会携带前轮用户输入、Hook 规则、reasoning/assistant 输出；本样本中 concise 规则每轮重复追加。
4. 三轮中 `history.for_prompt.items` 与 `final Prompt.input` 完全相等，说明这段路径在 `for_prompt` 后到 transport 前没有再次改写 input。
5. 首轮仅上下文可见文本就约 35,184 字符，另有 21,335 字符基础 instructions 和 17 个工具 schema；上下文体积主要不是用户问题造成的。

## 注意

原始文件包含完整指令、AGENTS.md、环境、工具 schema、reasoning 和回复，不应公开提交。该样本使用上游 Codex 模型链路，不是 `ds-codex` DeepSeek provider；它验证的是 harness 上下文组装行为。

