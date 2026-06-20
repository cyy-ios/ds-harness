# Context provenance trace 打点方案

## 位置

实现放在独立 worktree：

```text
C:\项目\ds-harness\context-trace
branch: context-provenance-trace
```

未修改 `codex/` 上游基线，也未修改 `ds-codex/` DeepSeek provider worktree。

## 开启方式

运行 Codex 前设置：

```powershell
$env:CODEX_CONTEXT_TRACE_DIR="C:\项目\ds-harness\internal\context-traces"
```

每个 thread 输出一个 JSONL 文件：

```text
<CODEX_CONTEXT_TRACE_DIR>/<thread_id>.jsonl
```

该 trace 会记录完整模型输入和 history 条目，可能包含用户隐私、文件内容、工具结果和环境信息；只用于本地研究，不应提交或公开。

## 已打点事件

| stage | action | 含义 | 兜底能力 |
|---|---|---|---|
| `history` | `append` | 每次 `Session::record_conversation_items` 写入 history 的条目 | 捕获用户输入、初始上下文、Hook additional_context、Skill/Plugin 注入、工具结果、assistant 输出等大部分新增项 |
| `history` | `replace` | `replace_history` / `replace_compacted_history` 替换整段 history | 捕获 compact、rollback/resume 等替换路径 |
| `history` | `for_prompt` | `clone_history().for_prompt(...)` 后真正送入采样前的 `input[]` | 捕获 normalize、能力过滤后的模型可见 history |
| `prompt` | `final_before_transport` | `client_session.stream(...)` 前的最终 `Prompt` | 捕获 `base_instructions`、`input[]`、`tools[]`、并行工具、人格和输出 schema |

## provenance 字段

`history.append` 使用 `#[track_caller]` 记录调用位置：

```json
"source": { "file": "...", "line": 3023, "column": 18 }
```

这可以把每段 history 反查到源码来源，例如：

- `record_context_updates_and_set_reference_context_item`：初始上下文或设置 diff。
- `hook_runtime::record_pending_input`：用户输入。
- `hook_runtime::record_additional_contexts`：Hook 追加上下文。
- `turn.rs` 注入项写入：Skill/Plugin/Extension 触发注入。
- `stream_events_utils` / `turn.rs::drain_in_flight`：assistant 输出或工具结果。

## 完整性校验方法

对同一个 `turn_id`：

1. 收集该 turn 前所有 `history.append` / `history.replace`。
2. 重放出期望 history。
3. 与最近一次 `history.for_prompt.payload.items` 对比。
4. 再与 `prompt.final_before_transport.payload.prompt.input` 对比。

如果 `append/replace` 重放结果与 `for_prompt` 不一致，差异通常来自 `ContextManager::for_prompt` 的 normalize、图片能力过滤、孤儿 tool output 清理等逻辑；如果 `for_prompt` 与最终 `prompt.input` 不一致，则说明 `build_prompt` 或 transport 前格式化还有额外变化。

## 当前验证

已在 `context-trace/codex-rs` 执行：

```powershell
& "$HOME\.cargo\bin\cargo.exe" check -p codex-core --lib --message-format short
```

结果：通过。

