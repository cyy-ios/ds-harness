# Data Harness 任务规格

本文定义 M1 必须实现的最小功能。

## 输入

- 支持读取 CSV 文件。
- 支持读取 JSONL 文件。
- 支持一次传入多个输入文件。
- 跳过空行。

## 处理规则

- 有 `id` 且 `id` 非空的记录计为 processed。
- 缺少 `id` 或 `id` 为空的记录计为 rejected。

## M1 验证命令

M1 固定用下面命令验证：

```bash
python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json
```

报告必须写到 `tmp/report.json`；`source_files` 必须按该命令中的输入顺序记录为 `["data/input.csv", "data/events.jsonl"]`。

## 输出报告

写出合法 JSON 报告，至少包含：

- `processed_count`
- `rejected_count`
- `retry_count`，M1 固定为 `0`
- `source_files`，按命令参数顺序记录输入文件相对路径

## Python 入口

- `import mini_harness` 必须成功。
- `from mini_harness.runner import run_dag, HarnessError` 必须成功。
- `run_dag` 执行数据处理。
- `HarnessError` 表示处理失败。

## 工程约束

- 只使用 Python 标准库。
- 不运行 `pip install`。
- 不硬编码本机绝对路径。
- 输入和输出路径来自命令参数。
- 代码和生成产物保持在当前 fixture 仓库内。
