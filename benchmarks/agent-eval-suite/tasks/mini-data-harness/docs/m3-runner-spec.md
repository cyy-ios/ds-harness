# M3 Runner 细节规格

M3 在 M1/M2 基础上实现 DAG runner、retry 和结构化日志。

## DAG stage

- runner 必须体现 `extract -> clean -> report` 三个 stage。
- stage 执行顺序必须是 `extract`、`clean`、`report`。
- `extract` 负责读取 CSV/JSONL 输入。
- `clean` 负责按 `id` 是否存在且非空分类 processed/rejected。
- `report` 负责写出 JSON 报告。

## Retry

- 实现 retry/attempt 机制。
- 最多重试 2 次。
- 报告中的 `retry_count` 反映实际发生的重试次数。

## 结构化日志

- 运行时输出结构化日志。
- 日志必须出现 `extract`、`clean`、`report`。
- 日志项必须包含 `stage`、`status`、`attempt`。

## 报告回归

- M1 固定命令仍生成正确报告。
- M2 默认 JSON 配置和显式 YAML 配置仍生效。
- 报告继续包含 `processed_count`、`rejected_count`、`retry_count`、`source_files`。
- 配置存在 `report_label` 时，报告继续写入 `report_label`。
