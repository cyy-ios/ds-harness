已创建 `mini_harness` 包并验证通过。

**包结构**

- `mini_harness/__init__.py` — 导出 `run_dag`, `HarnessError`
- `mini_harness/__main__.py` — `python -m mini_harness run ...` 入口
- `mini_harness/cli.py` — argparse CLI，`run` 子命令
- `mini_harness/runner.py` — 核心 DAG（`extract` → `clean` → `report`），含重试逻辑

**核验结果**

| 测试 | 结果 |
|------|------|
| `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` | processed=4, rejected=2, retries=0 |
| 含注释 CSV (`m4_noise_test.csv`) | processed=2, rejected=1 |
| `run_dag` / `HarnessError` 导出 | ✅ |
| 日志含 `attempt`/`stage`/`status` | ✅ |
| 报告含 `processed_count`/`rejected_count`/`retry_count`/`source_files` | ✅ |
| 报告引用 `memory/memory_summary.md` | ✅ |
| 无 `pip install`，纯 stdlib | ✅ |