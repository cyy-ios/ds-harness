已完成：新增 `mini_harness` 包、`run` 子命令、`python -m mini_harness run ...` 支持，以及 `run_dag` / `HarnessError` 导出。实现覆盖 CSV/JSONL 读取、snake_case 清洗、缺失 `id` rejects、三阶段 DAG、最多 2 次重试和报告日志字段。

已核验：
`python -B -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 通过。
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -q` 通过，`4 passed`。

按要求已读取并遵循 `skills/data-harness/SKILL.md`，复盘参考了 `memory/memory_summary.md`。当前改动仅剩新增 `mini_harness/` 和 `tests/test_mini_harness.py`。