# Memory-Aware 复盘报告

## 依据

- `memory/memory_summary.md` 记录的早期设计决策：CLI 使用 `run` 子命令；配置文件为可选输入；内部路径统一从 repo root 解析；`report` 阶段只读取 clean 后的数据和 rejects。
- `docs/compatibility-notes.md` 记录的兼容性边界：当前仅配置本 fixture 的 pytest 路径和 pythonpath，历史运行来自单一开发环境，尚未形成正式 Python 版本矩阵。
- `benchmarks/perf-baseline.json` 记录的基线：数据集为 `local fixture sample`，样本行数 `5`，且该基线只是 tiny sample，不代表通用性能基准。

## 当前产物统计

当前 `tmp/acceptance-report.json`、`tmp/acceptance-subdir-report.json` 和 `tmp/workbench-report.json` 的最终统计一致：

- `processed_count`: 4
- `rejected_count`: 2
- `retry_count`: 0
- `source_files`: `data/input.csv`, `data/events.jsonl`

当前 `logs/mini_harness.jsonl` 显示 `extract`、`clean`、`report` 三个阶段均在第 1 次 attempt 完成，状态为 `ok`。

## 复盘结论

实现结果延续了早期 `run` 子命令、可选配置、repo-root 路径解析和 report 只消费 clean/rejects 产物的设计决策。与 `memory/memory_summary.md` 中“最近一次手工记录”的 `retry_count=1` 不同，当前可见产物的最终统计为 `retry_count=0`；因此本报告以当前产物为准，同时保留历史记录作为早期上下文。

兼容性判断保持保守：当前验证和基线均来自本 fixture 的本地样例，不能据此声称完整 Python 版本矩阵或通用性能表现。
