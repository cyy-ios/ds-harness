Codex 的 context 是“分层注入 + 历史持久化 + 增量 diff + 触发式压缩 + memory 独立读写再以工具/摘要进入上下文”的体系，不是把所有记忆和历史无脑塞进 prompt。

  Context 生成

  - 入口：codex-rs/core/src/session/mod.rs::build_initial_context
  - 组成：developer 区和 contextual user 区分离。
  - developer 区：权限、协作模式、模型切换、realtime、personality、apps、skills、plugins、extension context。
  - contextual user 区：AGENTS.md/用户指令、环境信息、cwd/shell/date/timezone/network/filesystem/subagents。
  - 片段模型：codex-rs/core/src/context/* 和 codex-rs/context-fragments/src/*，每类上下文封装成 fragment，最后转成 ResponseItem::Message。

  Context 注入策略

  - 首轮或 reference 缺失：注入完整 initial context。
  - 后续轮次：只注入变化 diff，减少 token。
  - 关键实现：codex-rs/core/src/context_manager/updates.rs
  - baseline：TurnContextItem 作为 reference context，被持久化到 rollout；恢复/回滚后可重建 diff 基线。
  - 设计重点：上下文不是一次性字符串，而是可识别、可 diff、可 rollback 的结构化片段。

  历史处理

  - 核心对象：ContextManager，文件：codex-rs/core/src/context_manager/history.rs
  - 内存中维护 Vec<ResponseItem>，只记录 API 可见项，过滤 system/Other/CompactionTrigger。
  - for_prompt() 发送前做 normalize：补齐 call-output 对、移除 orphan output、不支持 image 时剥离 image。
  - tool/function output 会按 token 策略截断，避免工具输出污染窗口。
  - token 估算用启发式，不依赖精确 tokenizer：文本按字节估，image 和 encrypted reasoning 有专门估算。


  Memory 策略

  - Memory 写入不直接进普通对话历史，而是独立 pipeline。
  - 文档：codex-rs/memories/README.md
  - Phase 1：后台扫描符合条件的旧 rollout，提取 per-thread raw_memory、rollout_summary、rollout_slug，写入 state DB。
  - Phase 2：选择高价值 stage1 outputs，生成/更新 ~/.codex/memories 下的 raw_memories.md、rollout_summaries/、memory_summary.md 等，并用内部 consolidation agent 维护。
  - 触发条件：root session 启动、非 ephemeral、MemoryTool 开启、非 subagent、state DB 可用。

  Memory 如何进入上下文

  - read path 通过 extension 注入 developer prompt，而不是把全部 memory 塞进历史。
  - 入口：codex-rs/ext/memories/src/extension.rs
  - 注入内容：读取 ~/.codex/memories/memory_summary.md，截断后渲染成 developer instructions。
  - 同时暴露 dedicated memory tools：list/read/search/ad_hoc_note，让模型按需读取详细 memory。
  - citation 会被解析并记录 usage，影响后续 phase2 选择：stream_events_utils.rs + record_stage1_output_usage。

  History 策略

  - 对话线程历史：thread-store / rollout JSONL，支持 resume、fork、rollback、read。
  - 用户输入历史：~/.codex/history.jsonl，由 codex-rs/message-history/src/lib.rs 维护，只用于输入历史/检索，不等同 prompt context。
  - thread history 会参与 prompt；message history 不直接合入 prompt。
  - rollout history 是 canonical replay source，state DB 是索引/元数据/搜索/记忆任务调度层。


  压缩 / Compact

  - 手动 compact：codex-rs/core/src/tasks/compact.rs
  - 本地 compact：codex-rs/core/src/compact.rs
  - 远程 compact：codex-rs/core/src/compact_remote.rs
  - 自动 compact 根据 token 状态触发；context window exceeded 时优先删最旧历史项，保留近期上下文。
  - 本地 compact 流程：把 compact prompt 作为用户输入跑一次模型，取最后 assistant summary，再构造 replacement history：保留最近用户消息 + summary。
  - 远程 compact 流程：把历史送 compact endpoint，返回 replacement history；返回后过滤 stale developer/user context，再按需要重新注入当前 canonical context。
  - 关键策略：compact 后不是保留旧 prompt 前缀，而是安装 replacement history，并清/重设 reference_context_item，保证后续 context diff 不基于过期上下文。



  核心设计可迁移点

  - ContextFragment 化：每类上下文独立可 render、可识别、可回滚。
  - TurnContextItem baseline：用结构快照做 diff，而不是每轮重复注入。
  - context 与 memory 分离：memory 先异步沉淀，prompt 只注入 summary + tools。
  - compact 安装 replacement history：压缩是历史重写，不是简单追加摘要。
  - hook/extension 可贡献 additional context，但要有 slot、预算和可追踪来源。
