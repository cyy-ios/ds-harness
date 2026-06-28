# M1_bootstrap 完整需求基线

本文档是供任务设计者和检查点设计者使用的 M1 内部完整版需求。后续拆分原子检查点时，以本文档为唯一需求来源；本文档不描述这些要求如何向被测 Agent 披露。

## 任务目标

当前 fixture 仓库没有 `mini_harness` 实现。M1 要求从零创建首个最小可运行版本，使其能处理预置的 CSV/JSONL 数据，并同时支持命令行调用和 Python API 调用。

## Python 包与 API

1. 创建名为 `mini_harness` 的 Python 包。
2. `import mini_harness` 必须成功。
3. 以下导入必须成功：

   ```python
   from mini_harness.runner import run_dag, HarnessError
   ```

4. `run_dag` 是实际执行数据处理的 Python API 入口。
5. CLI 必须调用 `run_dag`，不能维护另一套独立的数据处理实现。
6. `HarnessError` 是包内用于表示处理失败的异常类型。

## 命令行接口

以下命令必须能在 fixture 仓库根目录成功运行：

```bash
python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json
```

命令要求：

- `run` 是执行一次数据处理任务的子命令；
- 支持传入一个或多个输入文件；
- 通过 `--output` 接收报告输出路径；
- 本次命令读取 `data/input.csv` 和 `data/events.jsonl`；
- 将合法 JSON 报告写入 `tmp/report.json`。

## 数据处理规则

- 支持读取 CSV 文件；
- 支持读取 JSONL 文件；
- 合并处理多个输入文件中的记录；
- 跳过空行；
- 将字段名规范化为 `snake_case`；
- `id` 存在且非空的记录计为 processed；
- `id` 缺失或为空的记录计为 rejected。

## 报告要求

报告必须是合法 JSON，并至少包含：

- `processed_count`：成功处理的有效记录数；
- `rejected_count`：被拒绝的无效记录数；
- `retry_count`：M1 固定为 `0`；
- `source_files`：输入文件相对 fixture 仓库的路径，顺序与命令参数一致。

对 fixture 预置输入，正确结果为：

```json
{
  "processed_count": 4,
  "rejected_count": 2,
  "retry_count": 0,
  "source_files": ["data/input.csv", "data/events.jsonl"]
}
```

4/2 的准确计数属于内部预期结果，不要求直接披露给被测 Agent。

## 工程约束

- 实现和生成产物必须留在 fixture 仓库内；
- 只使用 Python 标准库；
- 不安装依赖，不修改全局环境；
- 不硬编码工作站绝对路径；
- 输入和输出路径来自命令参数。

## 验证要求

Agent 必须使用仓库内命令验证 CLI 能运行并生成报告。最低相关验证是运行上述 CLI 命令，并确认命令成功且报告符合要求。

## M1 边界

JSON/YAML 配置解析、完整重试机制、结构化日志、cwd 切换行为、memory-aware 报告和 compact resume 属于后续里程碑，不是 M1 完成的必要条件。该边界用于内部设计和检查点拆分，不要求向被测 Agent 披露。
