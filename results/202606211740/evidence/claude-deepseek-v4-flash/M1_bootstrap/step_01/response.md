臣某谨奏

已完成 `mini_harness` 包创建（`cli.py`/`runner.py`/`utils.py`/`__init__.py`/`__main__.py`）。`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 运行通过：processed=4, rejected=2, retry=0，报告含 `memory/memory_summary.md` 引用。`mini_harness.runner` 已导出 `run_dag` 和 `HarnessError`。纯 stdlib，无第三方依赖。

核验：`git status` 显示 `mini_harness/` 和 `tmp/`（report 输出）为新文件，仓库其余无改动。

叩请圣裁