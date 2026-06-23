---
name: data-harness
description: Use for implementing the mini data processing harness fixture.
---

# Data Harness Skill

必须遵守：
- 禁止 `pip install` 或依赖未声明第三方包；CLI 优先用 argparse。
- 输入支持 CSV 和 JSONL。
- 清洗规则：去除空行；字段名转 snake_case；缺少 `id` 的记录进入 rejects。
- DAG 任务必须有 `extract`、`clean`、`report` 三个阶段。
- 失败重试最多 2 次；日志必须包含 `attempt`、`stage`、`status`。
- 报告必须包含 `processed_count`、`rejected_count`、`retry_count`、`source_files`。
- 包必须支持 `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json`。
- `mini_harness.runner` 必须导出 `run_dag` 和 `HarnessError`。
- 最终复盘报告必须引用 `memory/memory_summary.md`。
