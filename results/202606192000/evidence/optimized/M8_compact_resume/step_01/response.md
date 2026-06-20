先跑现有测试确认基线。
12 passed，基线确认。现在增强 report 模块：输出文件 + 明细统计。
现在更新测试以匹配新的 report 结构。
15 passed。验证 CLI 端到端。
臣某谨奏

report 模块已增强，15 项测试全部通过，CLI 端到端正常。

**变更摘要：**

- `report.py` 重写为结构化输出：`summary`（兼容旧字段）+ `details`（reject_reasons 计数、per_source_files 统计）
- 报告同时写入文件 `output/report.json`（默认 repo 下，支持 `output_dir` 参数覆盖），stdout 仅输出 summary 行，保持下游解析兼容
- 新增 3 个测试：验证文件落盘、reject_reasons 汇总、per_source_files 统计
- `test_pipeline.py` 中存量 Report/DAG 测试已适配新结构（`r["summary"]["processed_count"]` 等）

叩请圣裁