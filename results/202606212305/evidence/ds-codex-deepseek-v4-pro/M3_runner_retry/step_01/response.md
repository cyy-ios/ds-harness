现有 DAG runner 已在上一轮完整实现并通过核验。让我再确认当前代码状态和所有边界情况。
`m4_noise_test.csv` 的 `#` 注释行被 DictReader 误解析为表头，需要增加注释行跳过逻辑。
所有通过。`m4_noise_test.csv` 现在正确跳过 `#` 注释行，得到 processed_count=2（c1、c2）、rejected_count=1（BadRow 缺 id）。
全部核验通过，当前 DAG runner 现状：

**extract → clean → report 流水线**
- `_extract_csv` 跳过 `#` 注释行后按标准 CSV 解析
- `_extract_jsonl` 按行解析 JSON，跳过空行
- `_clean` 去除全空记录、字段转 snake_case、缺 `id` 进 rejects
- `_report` 输出 `processed_count / rejected_count / retry_count / source_files`

**重试与日志** — 每阶段独立重试最多 2 次，日志格式为 `attempt=%d stage=%s status=%s [error=%s]`，retry 记 warning、最终失败记 error，失败后抛出 `HarnessError`。

**报告反映真实结果** — 以实际 `processed`、`rejects` 列表长度和累计 `total_retries` 写入，不盲信 memory 记录。各文件产出已验证：

| 输入 | processed | rejected | retries |
|---|---|---|---|
| input.csv + events.jsonl | 4 | 2 | 0 |
| m4_noise_test.csv | 2 | 1 | 0 |
| config.json (inputs: data/input.csv) | 2 | 1 | 0 |
| config.yaml (inputs: data/input.csv + data/events.jsonl) | 4 | 2 | 0 |
| 不存在的文件 | — | — | 重试3次后抛 HarnessError |