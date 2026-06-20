# Codex 上下文层实现

## 边界

上下文层负责决定模型每次采样实际看到什么、以什么顺序看到、何时更新、如何压缩，以及恢复后如何保持语义连续。Provider 只负责把最终 `Prompt` 映射到模型 API；工具执行和任务状态机分别属于工具层与 Agent Loop/运行时层。

## 文件结构

```text
codex/codex-rs/
├─ core/
│  ├─ *.md                              # 模型基础指令与模型专用 prompt
│  ├─ src/agents_md.rs                  # AGENTS.md/override/fallback 分层发现、拼接、字节预算
│  ├─ src/session/
│  │  ├─ mod.rs                         # 会话初始化、基础/开发者/用户指令来源与优先级
│  │  ├─ turn_context.rs                # 每轮解析后的模型、环境、指令、压缩配置快照
│  │  ├─ turn.rs                        # 每轮输入组装、动态扩展、采样前压缩、Prompt 构造
│  │  └─ rollout_reconstruction.rs      # 恢复会话时重建模型可见历史
│  ├─ src/context/                      # 各类结构化上下文片段
│  │  ├─ environment_context.rs         # cwd、shell、日期、时区、文件系统、子环境
│  │  ├─ permissions_instructions.rs    # 沙箱、审批和网络权限
│  │  ├─ user_instructions.rs           # AGENTS.md 等用户级指令
│  │  ├─ collaboration_mode_instructions.rs # Plan/Default 等协作模式的开发者约束
│  │  ├─ available_skills_instructions.rs   # 当前可用 Skill 清单和使用规则
│  │  ├─ available_plugins_instructions.rs  # 当前可用插件清单和插件使用规则
│  │  ├─ model_switch_instructions.rs       # 模型切换后的能力/行为更新提示
│  │  ├─ personality_spec_instructions.rs   # 人格/输出风格约束注入
│  │  ├─ hook_additional_context.rs         # hook 返回的额外上下文片段
│  │  └─ contextual_user_message.rs     # 识别/分类可更新的上下文消息
│  ├─ src/context_manager/                 # 模型可见历史的维护、归一化和更新生成
│  │  ├─ history.rs                     # 模型可见历史、token/字节估算、截断与回滚
│  │  ├─ normalize.rs                   # tool call/output 配对、孤儿清理、能力兼容
│  │  └─ updates.rs                     # 环境、权限、模式、模型、人格的增量更新消息
│  ├─ src/compact.rs                    # 本地摘要压缩与初始上下文重注入
│  ├─ src/compact_remote.rs             # Responses compact v1、工具输出降级与裁剪
│  ├─ src/compact_remote_v2.rs          # compact v2、保留项选择与消息 token 预算
│  ├─ src/state/auto_compact_window.rs  # 自动压缩窗口及 prefill 计量
│  ├─ src/prompt_debug.rs               # 导出最终模型输入，支持上下文审计
│  ├─ src/realtime_context.rs            # 实时会话上下文选取
│  └─ src/thread_rollout_truncation.rs   # rollout 过大时的存储/恢复裁剪
├─ core-skills/src/                        # Skill 加载、选择、注入和元数据渲染
│  ├─ loader.rs / manager.rs            # Skill 发现、加载与状态
│  ├─ injection.rs                      # 显式提及识别和按需注入 SKILL.md
│  └─ render.rs                         # 可用 Skill 元数据预算、截断、排序、路径别名
├─ ext/skills/src/                      # Skill 作为 extension 的 catalog/provider/fragment
├─ ext/memories/src/                    # memory 工具及其 developer instructions
├─ context-fragments/src/               # extension 向 prompt 注入结构化片段的接口
├─ prompts/src/ + prompts/templates/    # compact、permissions、goals、agents 等模板
├─ hooks/src/events/                    # user-prompt-submit、pre/post-compact 上下文钩子
├─ rollout/ + state/                    # 历史持久化、恢复和压缩记录
└─ response-debug-context/              # 请求调试上下文
```

`tui/`、`app-server/` 主要提供输入与展示，不是上下文语义的事实来源；`model-provider/`、`codex-api/` 是最终请求传输边界。

## 主流程

1. 会话启动时选择模型基础指令；配置覆盖优先于模型默认指令。
2. 读取 developer instructions，并从全局到项目当前目录加载 `AGENTS.override.md`、`AGENTS.md` 或 fallback 文件；越具体的目录越靠后。
3. 构造权限、环境、用户规则、Skills、Plugins、人格和协作模式等结构化消息。
4. 每轮将用户输入、hook/extension 附加上下文和工具结果写入 `ContextManager`；配置变化以新消息增量追加，不改写旧前缀。
5. `normalize` 保证 tool call 与 output 配对，删除孤儿输出，并按模型能力移除不支持的图片。
6. 采样前估算模型可见 token；达到阈值时选择本地摘要、remote compact v1 或 v2，随后重注入必要初始上下文。
7. `build_prompt` 将基础指令、规范化历史和工具定义组成最终请求；恢复、fork、rollback 使用同一历史语义重建路径。

## 已实现的优化策略

### 指令与前缀

- **稳定前缀优先**：基础指令和长期规则放前面，动态用户输入放后面，提高 prompt cache 命中率。
- **增量上下文更新**：cwd、权限、协作模式、人格或模型变化时追加差异消息，避免重写历史和破坏缓存。
- **分层项目规则**：AGENTS 文件从项目根到 cwd 拼接，`AGENTS.override.md` 优先，支持 fallback 名称和总字节上限。
- **结构化边界标签**：权限、环境、规则等使用固定片段类型/标签，降低不同来源混淆。
- **模型专用基础指令**：按 model family 选择 prompt，并允许配置覆盖；切换模型时补充更新消息。

### Skills、Plugins 与动态上下文

- **渐进披露**：启动时主要注入 Skill 元数据，明确提及后再注入完整 `SKILL.md`。
- **元数据预算**：按上下文窗口计算 Skill 元数据预算，排序、截断描述，并至少保留最小可发现信息。
- **路径压缩**：对重复 Skill 根目录生成别名，仅在总成本更低时采用。
- **显式提及解析**：识别 `$skill`、链接和工具路径，避免无关 Skill 全量进入当前轮。
- **Extension fragments**：插件、memory、hooks 通过受控片段注入，而不是任意改写基础历史。

### 历史完整性与降噪

- **调用结果配对修复**：缺失 tool output 时补占位结果，删除无对应调用的孤儿输出，保持 API 历史合法。
- **能力归一化**：模型不支持图片时剥离图片项；不同消息形态统一后再采样。
- **工具输出截断**：对过大 function output 按策略裁剪，并保留模型继续判断所需的错误/边界信息。
- **模型可见成本估算**：分别估算文本、reasoning、加密函数输出和 data URL 图片，而非只统计原始 JSON 大小。
- **用户轮次边界保护**：回滚、裁剪和恢复以真实用户轮次为边界，避免切断一组语义事件。

### 压缩与长上下文

- **自动阈值压缩**：同时考虑模型自动压缩阈值和完整 context window 上限。
- **窗口化计量**：记录每个压缩窗口的 prefill，避免压缩后 token 计数失真或立即重复压缩。
- **多后端策略**：按 provider 能力选择本地摘要、remote compact v1 或 v2。
- **初始上下文重注入**：压缩后在最后一个真实用户消息或 summary 前恢复必要环境/规则，防止摘要丢失当前执行条件。
- **保留关键项**：remote compact 对必须保留的消息单独筛选；v2 对保留消息设置 token 预算并做文本级截断。
- **超窗降级**：compact 请求仍过大时先重写/缩短函数输出，再重试，而不是直接丢弃整段历史。
- **模型切换保护**：切换到更小窗口模型前执行预采样压缩，并清理只对旧模型有效的临时上下文形态。

### 恢复与可观测性

- **统一重建**：resume、fork、rollback 从 rollout 事件重建模型可见历史，并清理回滚点之后的上下文更新。
- **Prompt 调试导出**：`prompt_debug` 可生成最终 input，用于比较“配置预期”与“模型实际看到”。
- **压缩钩子与事件**：pre/post-compact hooks、事件和 trace 支持定位信息在何处丢失。
- **缓存键隔离**：不同线程/审查会话可使用独立 prompt cache key，避免错误复用。

## 深入研究顺序

1. **最终输入基线**：用 `prompt_debug` 和请求 trace 固化首轮、第 3/10/20 轮、工具失败后、压缩后、恢复后的完整模型可见输入。
2. **指令有效密度**：统计基础指令、AGENTS、Skills、插件和动态片段的 token 占比、重复、冲突及实际触发率。
3. **历史反馈质量**：检查工具输出截断前后、错误包装、调用配对修复是否保留了正确下一步所需证据。
4. **压缩保真度**：建立事实、约束、未完成动作、文件状态和验证结果清单，对 local/v1/v2 压缩做逐项保持率测试。
5. **动态更新一致性**：测试 cwd、权限、模型、协作模式变化以及 resume/fork/rollback 后，旧规则是否被错误保留或新规则是否遗漏。
6. **消融优化**：依次消融 Skill 元数据、重复规则、动态片段、压缩策略和截断阈值，只保留同任务同预算下可重复提升完成率的改动。

对 Agent 智力影响最大的上下文子块通常是：**指令冲突与有效密度 > 工具结果在历史中的信息质量 > 压缩保真度 > 动态环境一致性 > prompt cache/传输成本优化**。缓存和路径别名主要改善成本与延迟，只有在释放出的窗口避免关键上下文被挤出时才间接提升任务能力。
