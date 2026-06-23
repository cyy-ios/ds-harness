臣某谨奏

已完成。`mini_harness` 包已创建在 repo 根目录，`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 运行正常，输出 `{"processed_count": 4, "rejected_count": 2, "retry_count": 0, "source_files": [...]}`。

改动文件：
- `mini_harness/__init__.py` — 包入口
- `mini_harness/__main__.py` — `python -m` 入口
- `mini_harness/cli.py` — argparse CLI，`run` 子命令
- `mini_harness/extract.py` — CSV/JSONL 提取
- `mini_harness/clean.py` — snake_case 转换、空行剔除、缺 id 入 rejects
- `mini_harness/report.py` — JSON 报告生成（含 os.makedirs）
- `mini_harness/runner.py` — DAG extract→clean→report，最多 2 次重试，导出 `run_dag` 和 `HarnessError`
- `pyproject.toml` — pythonpath 改为 `["."]`
- 删除空的 `src/` 目录

`python -m pytest tests/` 1 passed。

叩请圣裁