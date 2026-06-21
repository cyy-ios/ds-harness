当前实现已有 DAG 和重试骨架；我会补强报告里的真实清洗记录和失败日志信息，并加一个重试行为测试。
我会先确认当前文件状态和实现细节，然后只补齐 DAG runner 的重试日志、真实结果报告和覆盖测试。
当前实现已有三阶段和配置解析；我会把失败日志补成结构化错误记录，把报告加入清洗后的真实 records，并添加一次失败后重试成功的单测。
接下来补测试断言，覆盖报告 records 与 retry_count/failed log 的实际行为。
测试里现在直接通过模块调用 runner，避免私有函数 patch 影响不到目标引用；我开始用仓库内 unittest 和 CLI 做核验。
单测和 `python -m mini_harness run ...` 都已通过；我再检查是否产生 `__pycache__`，并看一下最终 diff 范围。
已完成：`extract/clean/report` DAG runner 现在输出真实清洗记录 `records`，失败日志包含 `attempt/stage/status/error`，重试上限保持为最多 2 次，并新增了重试行为测试。

已核验：`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests` 通过 6 个测试，`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 通过，未产生 `__pycache__`；复盘引用：`memory/memory_summary.md`。