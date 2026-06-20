# 本次会话样本：用户输入到模型输入的最小链路

## 目标

用本次真实多轮对话做样本，解释 Codex 源码中“一条用户输入如何进入 history，并被 `build_prompt` 发送给模型”。本文只覆盖普通文本回复链路；工具调用、压缩、Goal continuation、恢复和 fork 后续单独研究。

## 真实源码主链

```text
Session::new_turn_from_configuration / new_turn_context_from_configuration
→ run_turn(sess, turn_context, input, ...)
→ record_context_updates_and_set_reference_context_item(turn_context)
→ build_skills_and_plugins(..., input, ...)
→ run_hooks_and_record_inputs(..., input)
→ record_conversation_items(injection_items)
→ clone_history().for_prompt(...)
→ run_sampling_request(..., sampling_request_input, ...)
→ build_prompt(input, router, turn_context, base_instructions)
→ client.rs::build_responses_request(prompt)
→ client_session.stream(...)
→ ResponseEvent::* 流式处理
→ 普通 assistant 文本变成 TurnItem::AgentMessage 并展示
```

关键源码入口：

| 阶段 | 文件 | 位置 |
|---|---|---|
| 构建 `TurnContext` | `codex-rs/core/src/session/turn_context.rs` | `new_turn_context_from_configuration` |
| 本轮主循环 | `codex-rs/core/src/session/turn.rs` | `run_turn` |
| 初始/增量上下文 | `codex-rs/core/src/session/mod.rs` | `build_initial_context`、`record_context_updates_and_set_reference_context_item` |
| 用户输入入 history | `codex-rs/core/src/hook_runtime.rs`、`session/mod.rs` | `record_pending_input`、`record_user_prompt_and_emit_turn_item` |
| 生成 Prompt | `codex-rs/core/src/session/turn.rs` | `build_prompt` |
| 请求字段 | `codex-rs/core/src/client_common.rs`、`client.rs` | `Prompt`、`build_responses_request` |
| 流式输出 | `codex-rs/core/src/session/turn.rs`、`stream_events_utils.rs` | `try_run_sampling_request`、`handle_output_item_done` |

## 源码确认的顺序

### 1. `TurnContext` 先于 `run_turn` 存在

`run_turn` 的参数已经包含 `turn_context: Arc<TurnContext>`。因此更准确说法不是“`run_turn` 创建 TurnContext”，而是：进入 `run_turn` 前，Session 已根据本轮配置生成 `TurnContext`。

`TurnContext` 包含本轮内部配置，例如：

```text
model_info / provider / cwd / environments / permission_profile / approval_policy
developer_instructions / user_instructions / turn_skills / collaboration_mode
reasoning_effort / compact_prompt / final_output_json_schema / extension_data
```

它不是一条直接发送给模型的消息，而是后续构造上下文、工具、权限和请求参数的配置快照。

### 2. `run_turn` 先写上下文，再处理用户输入

`run_turn` 开始后先做：

```text
run_pre_sampling_compact
record_context_updates_and_set_reference_context_item
build_skills_and_plugins
run_pending_session_start_hooks
run_hooks_and_record_inputs(input)
record_conversation_items(injection_items)
```

这意味着本轮进入模型前，history 的新增项通常是：

```text
上下文 full/diff 消息
→ 用户当前输入
→ user-prompt-submit hook 的 additional_context（如果有）
→ 本轮显式触发的 Skill/Plugin/Extension 注入项（如果有）
```

注意：Skill/Plugin 的完整注入项是先计算出来，但在用户输入记录之后才写入 history。

### 3. 初始上下文包含哪些模型可见内容

`build_initial_context` 会把多个来源聚合为 developer message 或 contextual user message：

| 来源 | 进入哪类消息 | 例子 |
|---|---|---|
| 权限说明 | developer | sandbox、approval、网络权限 |
| developer instructions | developer | 本次会话里的 concise 规则 |
| collaboration mode | developer | Default/Plan 模式规则 |
| personality/model switch | developer | 模型或人格变更提示 |
| app/plugin/skill metadata | developer | 可用 Skills/Plugins 清单 |
| extension fragments | developer 或 contextual user | Goal/Memory/Plugin 等扩展片段 |
| AGENTS/user instructions | contextual user | 项目规则、用户规则 |
| environment context | contextual user | cwd、shell、日期、时区、文件系统权限 |

如果已经有 reference context，`record_context_updates_and_set_reference_context_item` 不会每轮重注入完整上下文，而是只追加设置差异；如果缺失 baseline，则注入完整 `build_initial_context`。

### 4. 用户输入如何进入 history

`run_hooks_and_record_inputs` 对每个 `TurnInput::UserInput` 执行：

```text
inspect_pending_input
→ user-prompt-submit hook 可检查输入并返回 additional_context/阻止
→ record_pending_input
→ record_user_prompt_and_emit_turn_item
→ ResponseInputItem::from(input) 转成 ResponseItem
→ record_conversation_items 写入 history
```

所以本次你发的每一句话，例如：

```text
你先理解我的意图
继续
```

都会作为新的 user message 进入 history；如果 hook 追加上下文，则追加的内容也会作为 contextual user fragment 进入 history。

### 5. `build_prompt` 真正发送什么

`build_prompt` 返回 `Prompt`：

```rust
Prompt {
    input,
    tools: router.model_visible_specs(),
    parallel_tool_calls,
    base_instructions,
    personality,
    output_schema,
    output_schema_strict,
}
```

`client.rs::build_responses_request` 再把它映射为 Responses 请求：

```text
instructions = prompt.base_instructions.text
input        = prompt.get_formatted_input()
tools        = create_tools_json_for_responses_api(prompt.tools)
tool_choice  = "auto"
stream       = true
reasoning / text / service_tier / prompt_cache_key ...
```

因此 Codex 不是把一个纯字符串 prompt 发给模型，而是发：

```text
instructions：模型基础指令
input：history 中模型可见的多条 ResponseItem
tools：模型可调用工具的 schema
其他参数：并行工具、reasoning、输出 schema、缓存 key 等
```

## 用本次会话还原一轮输入

以用户输入：

```text
你先理解我的意图
```

为例，模型请求里的关键内容可概括为：

```text
instructions:
  Codex/assistant 基础行为规则

input（按历史顺序，简化）:
  developer: 当前开发者规则，包括 concise 输出约束、工具/权限规则等
  user/contextual: environment_context，如 cwd=C:\项目\ds-harness、权限、日期等
  user: 之前关于 Goal、Updated Plan、四层架构、context 研究的多轮问题
  assistant: 之前每轮 assistant 回复
  user: “基于本次session的多轮对话……写入一个文档……”
  assistant/tool events: 创建过的文档和后续回复（若本轮之前已发生）
  user: “你先理解我的意图”

tools:
  shell/apply_patch/web 等当前可见工具 schema
```

模型看到这些后，并不是 Codex 代码先判断“用户在批评上一个文档太概念化”；而是模型从 history 中推断：用户要的是基于当前 session 的真实链路还原，而不是泛化解释。

## 本次“继续”这一轮在链路中的内容

用户输入：

```text
继续
```

各环节对应内容：

| 环节 | 本轮内容 |
|---|---|
| `TurnContext` | cwd=`C:\项目\ds-harness`，可写文件系统，当前 concise 规则，可用 shell/apply_patch/web 等工具，普通对话模式。 |
| context full/diff | 若 reference context 已存在，只追加本轮与上一轮不同的设置；通常没有完整重注入。 |
| user message | `继续` 原文进入 history。 |
| hook additional_context | 如果配置了 user-prompt-submit hook 且返回上下文，会紧跟用户输入写入；本次未观察到具体 hook 输出。 |
| skill/plugin injection | 若用户显式提及 Skill/Plugin，会在用户输入后追加完整说明；本轮“继续”未显式触发。 |
| prompt.input | 旧多轮 history + 本轮 context diff + `继续`。 |
| prompt.tools | 当前模型可见工具 schema。 |
| 模型决策 | 结合上一轮“你先理解我的意图”，继续做真实源码追踪并改写研究文档。 |

## 模型普通文本如何回到用户

普通文本返回路径：

```text
client_session.stream(prompt, ...)
→ ResponseEvent::OutputItemAdded
→ 创建/开始 TurnItem::AgentMessage
→ ResponseEvent::OutputTextDelta
→ AgentMessageContentDeltaEvent 流式发给客户端
→ ResponseEvent::OutputItemDone
→ handle_output_item_done
→ finalize_non_tool_response_item
→ emit_turn_item_completed
→ record_completed_response_item 写回 history
→ ResponseEvent::Completed(end_turn=true/None)
→ run_turn 结束
```

如果模型返回工具调用，则 `handle_output_item_done` 会设置 `needs_follow_up=true`，Codex 执行工具并把工具结果写回 history，再进入下一次采样；这不属于本文“普通文本最小链路”。

## 当前仍未还原的内容

仅凭对话文本，不能精确还原当前运行时的完整 `Prompt.input` JSON、每个工具 schema 和 token 数。要精确还原，需要使用 Codex 的 `prompt_debug`、rollout trace 或在 `client.rs::build_responses_request` 前打点导出请求。

下一步应建立一个可复现的小样本：输入一句固定文本，导出 `Prompt`，对照上述源码链路逐项标注每个 `ResponseItem` 的来源。
