Snake case 正确。检查 pycache 和最终报告。
全部 6 个测试通过。清理 __pycache__ 并最终核验。
全部 7 个测试通过（含原有 placeholder）。final 检查无 pycache 残留。
臣某谨奏

`mini_harness` 包已创建并核验通过。

**包结构** (`src/mini_harness/`)：`__init__.py`、`__main__.py`、`cli.py`、`pipeline.py`、`extract.py`、`clean.py`、`report.py`，共 7 文件。

**CLI 用法**：`python -B -m mini_harness run --input data/input.csv`

**实现要点**：
- 输入支持 CSV/JSONL（按扩展名推断）
- 清洗：空行丢弃、字段转 snake_case、缺 `id` 入 rejects
- DAG 三阶段 `extract → clean → report`，每阶段失败重试最多 2 次
- 日志含 `attempt/stage/status`，报告含 `processed_count/rejected_count/retry_count/source_files` 并引用 `memory/memory_summary.md`
- 零第三方依赖，纯标准库 + argparse
- `sitecustomize.py` + `__init__.py` 双保险防 pycache 污染

**核验结果**：`python -B -m pytest tests` 7/7 通过；`python -B -m mini_harness run` 对 CSV 和 JSONL 均产出正确的 report/logs；无 `__pycache__` 残留。

叩请圣裁