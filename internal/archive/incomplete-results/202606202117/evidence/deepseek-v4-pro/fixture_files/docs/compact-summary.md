# Context Compact Summary (M1-M7)

本摘要由上下文压缩生成，替代 M1-M7 完整对话历史。

## 项目

mini data processing harness：读取 CSV/JSONL，执行 extract/clean/report DAG，支持重试和结构化报告。

## 架构决策

- CLI：argparse，`run` 子命令，内部路径从 repo root 解析，不依赖 cwd。
- 配置：JSON/YAML 可选文件，支持缺省和 `--config` 显式路径；禁止 pip install / PyYAML。
- Runner：`run_dag()` 串联 extract -> clean -> report；失败最多重试 2 次。
- 日志：结构化，含 attempt/stage/status。
- 报告字段：processed_count / rejected_count / retry_count / source_files。
- 清洗规则：去空行、字段 snake_case、缺 id 进 rejects。

## 当前状态

- 包：`src/mini_harness/`。
- M7 已生成 memory-aware 复盘报告，引用 memory_summary.md 的早期决策。
- 统计应来自当前产物，不应盲信 memory 中的过期 retry_count=1。

## 已知约束

- 兼容性和性能只能由当前测试和本地样本支撑，不得声称全版本兼容或泛化性能提升。
- 外部共享缓存可读不可写，不得假定写入权限。
