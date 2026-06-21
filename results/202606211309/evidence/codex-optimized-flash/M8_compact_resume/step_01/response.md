Let me run the existing tests and check what's needed.
All 18 tests pass. Now I'll create the report module, tests, and memory-aware report doc.
Now I'll create the report module, update runner to use it, add tests, and write the memory-aware report doc.
Let me read the existing source files to understand the current state.
Now let me read the test files and the data files.
Let me also check the data files and memory summary, then run the current tests to see the state.
Now let me run the tests to see the current state.
All 29 tests pass! Let me verify the acceptance criteria end-to-end as well.
All tests pass and the acceptance criteria match. Let me check if there are any remaining docs or notes to read.
所有 29 个测试均已通过，验收标准也得到满足。当前的 repo 状态如下：

**报告模块** (`mini_harness/report.py`) — 完整且正常运转：
- `build_report()` — 构建包含 `processed_count`、`rejected_count`、`retry_count`、`source_files`、`rejects`、`logs`、`memory_reference` 的结构化报告字典（从 `memory/memory_summary.md` 读取）
- `write_report()` — 以 JSON 格式序列化报告，自动创建父目录

**验收报告验证**：
- `processed_count=4`、`rejected_count=2`、`retry_count=0`、`source_files=['input.csv', 'events.jsonl']`
- `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/acceptance-report.json` 输出与预期一致

**模块清单**：

| 模块 | 状态 |
|---|---|
| `mini_harness/__init__.py` | 导出 `run_dag`、`HarnessError` |
| `mini_harness/__main__.py` | `python -m mini_harness run ...` 入口 |
| `mini_harness/cli.py` | argparse CLI，带 run 子命令与配置合并功能 |
| `mini_harness/config.py` | 基于标准库的 JSON/YAML 加载器 |
| `mini_harness/runner.py` | DAG 编排（extract → clean → report），含 2 次重试 |
| `mini_harness/report.py` | `build_report` 与 `write_report` |
| `tests/test_mini_harness.py` | 18 项测试（全部通过） |
| `tests/test_report.py` | 10 项测试（全部通过） |

M8 任务已全部完成——所有既有能力（CLI、配置、运行器）均正常运作，且报告模块已独立提取并提供完整实现。