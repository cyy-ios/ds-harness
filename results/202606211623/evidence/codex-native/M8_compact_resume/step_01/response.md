已新增 `mini_harness.report` 并同步到 `src/mini_harness`，runner 的 report 阶段现在通过该模块生成/写入报告，保留 CLI、config、run_dag/HarnessError 行为。

已验证：`python -m pytest -q` 通过 `10 passed`，CLI 输出仍为 `processed_count=4、rejected_count=2、retry_count=0`。