现在修复两个 bug 并核验。
全部 8 项测试通过。接着核验 `python -m mini_harness run` 在两个工作目录下均可用。
CLI 在两处均正常。现在提取当前统计数据生成复盘报告。
现在让我运行测试确认当前状态，然后编写复盘报告。
复盘报告已写入 [docs/retrospective.md](/C:/项目/ds-harness/tmp/agent-eval-fixture-20260621230522/docs/retrospective.md:1)。核心结论：

**设计决策全部落实** — CLI `run` 子命令、可选 JSON/YAML 配置、repo-root 路径解析、report 只读 clean 后数据、DAG 三阶段串行重试，六项均与 `memory/memory_summary.md` 一致且通过测试验证。

**memory 偏差已纠正** — memory 声称 `retry_count=1`，但 `verify_final.json`、`acceptance-report.json`、`acceptance-m4-noise-report.json` 三份实报均为 `retry_count=0`。正向流程无阶段失败不触发重试计数，手工记录为陈旧值。

**中断项已处理** — `unrelated_error.log` 是外部缓存超时自行恢复，与 mini_harness 无关；`handoff-note.md` 为交接草稿，内容与现状一致。两项均不阻塞主线。

**测试全部通过** — 8 项 (root 5 + subdir 3)，覆盖 DAG、重试、配置解析、默认值、跨目录可用性。兼容性矩阵和性能基线仍为最小覆盖，生产使用前需扩展。