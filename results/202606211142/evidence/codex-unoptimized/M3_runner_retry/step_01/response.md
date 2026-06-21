已完成：DAG runner 现在明确输出 `extract/clean/report` 结构化日志、真实 `records/rejects`、真实计数和 `retry_count`，并补齐了最多 2 次重试的测试覆盖；同时修正 camelCase 字段转 `snake_case`，如 `eventType -> event_type`。

已核验：`python -B -m pytest -q` 通过，`7 passed`；`python -B -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 通过。复盘依据包含 `memory/memory_summary.md`。