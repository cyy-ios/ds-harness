已实现 `mini_harness` 包、`run` CLI、`python -m mini_harness run ...`、CSV/JSONL 提取、清洗 rejects、三阶段 DAG、重试日志和报告字段，并在报告中引用 `memory/memory_summary.md`。

已核验：`python -m pytest -q -p no:cacheprovider` 通过 `3 passed`；`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 成功生成报告。