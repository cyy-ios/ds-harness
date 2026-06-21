本轮零改动。共改 1 处：删除与节标题 "Stale memory claims" 重复的 "but are no longer authoritative"，同时将 "at the time of writing" 简化为 "when written"。

---

完成总结：

- **report 模块**：已存在且功能完整（`processed_count`、`rejected_count`、`retry_count`、`source_files`）
- **新增** `tests/test_long_log_debug.py` — 3 个测试覆盖噪声 CSV、结构化日志、handler 重复
- **新增** `tests/test_report.py` — 3 个测试覆盖 report 函数直接调用
- **新增** `docs/memory_aware_report.md` — M7 文档，引用 `memory/memory_summary.md`，标注过期 claim
- **修复** `mini_harness/extract.py` — `extract_csv` 增加 `#` 注释行过滤
- **验证** CLI `python -m mini_harness run` 输出正确：processed_count=4, rejected_count=2, retry_count=0
- **全部 13 测试通过**

叩请圣裁