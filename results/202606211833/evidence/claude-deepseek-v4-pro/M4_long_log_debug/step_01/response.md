臣某谨奏

定位问题：`runner.py` 模块级 `StreamHandler` 在 import 时就挂载，测试收集阶段即泄漏到 stderr。修复：将 handler 延迟到 `run_dag()` 首次调用时（`_ensure_logger()`），import 时零副作用。

新增 `tests/test_runner.py`（6 个测试）：DAG 输出报告、重试触发 HarnessError、rejects 含缺失 id、报告四字段、import 无 logger 泄漏。

`python -m pytest tests/ -v` → 7 passed。

叩请圣裁