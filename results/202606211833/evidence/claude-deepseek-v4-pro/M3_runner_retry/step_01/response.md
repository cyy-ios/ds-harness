臣某谨奏

DAG runner 已完善。extract → clean → report 三阶段流水线，最多 2 次重试（3 次尝试），结构化日志输出 JSON `{"attempt": N, "stage": "…", "status": "running|ok|failed"}` 到 stderr，报告包含 `rejected` 记录（真实处理结果），另写 `rejects.json` 侧车文件。

核验：
- 正常输入：processed=4, rejected=2 ✓
- 结构化日志：每阶段 attempt/stage/status ✓
- 重试行为：不存在的文件 → 3 次尝试后抛 HarnessError ✓
- `python -m pytest tests/` 1 passed ✓

改动文件：`mini_harness/runner.py`（日志 handler、rejects 侧写、错误上下文）、`mini_harness/report.py`（扩展 records.rejected 字段）。

叩请圣裁