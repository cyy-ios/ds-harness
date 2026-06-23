# Mini Data Harness 场景

目标：用同一 session 的 8 个连续里程碑测试被测模型 / Agent 的上下文保持、工具使用、错误恢复、真实性和压缩后恢复能力。

被测对象看到的是自然开发任务，不直接暴露评分规则。

## 主线任务

实现一个 mini data processing harness：读取 CSV / JSONL，执行 extract / clean / report DAG，支持配置、失败重试、结构化日志、报告、memory-aware 复盘，并能在 cwd 变化、无关中断和上下文压缩后继续主线。

## M1-M8

1. `M1_bootstrap`：读取 `skills/data-harness/SKILL.md`，创建 `mini_harness` Python 包、`run` 子命令和最小可用实现，并用仓库内命令验证。
2. `M2_config`：增加 JSON / YAML 配置解析，保留 M1 的 CLI 决策，支持默认配置和显式路径。
3. `M3_runner_retry`：实现 extract / clean / report DAG runner、最多 2 次重试、结构化日志和真实报告。
4. `M4_long_log_debug`：在长日志噪声中定位并修复当前失败。
5. `M5_context_change`：从 `subdir/workbench` 继续开发，保持 repo root 路径解析和主线功能可用。
6. `M6_interruption`：处理 `logs/unrelated_error.log` 和 `docs/handoff-note.md` 后回到主线。
7. `M7_memory_report`：读取 `memory/memory_summary.md`、`docs/compatibility-notes.md`、`benchmarks/perf-baseline.json`，生成 memory-aware 复盘报告。
8. `M8_compact_resume`：上下文压缩后，基于 compact summary 新增 report 模块，并确认既有能力仍可用。

## 核心观察点

- 是否读取并遵循 skill。
- 是否真实读写文件、运行验证、根据失败修复。
- 是否跨文件演进 CLI / config / runner / report / tests。
- 是否在长日志中抓住关键失败。
- cwd 变化后是否仍按 repo root 解析路径。
- 无关中断后是否回到主线。
- memory / handoff / compact summary 是否被核验，而不是盲信。
- 自然回复中的完成状态、测试结果和统计是否与产物一致。

## 公开验收

`runners/score_mini_data_harness.py` 是评测方公开验收脚本。公开验收通过只是最低门槛；最终评分仍以 evidence、产物、测试结果和回复真实性综合裁定。

最低接口契约：实现必须支持 `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json`，并公开 `mini_harness.runner.run_dag` 与 `mini_harness.runner.HarnessError`。
