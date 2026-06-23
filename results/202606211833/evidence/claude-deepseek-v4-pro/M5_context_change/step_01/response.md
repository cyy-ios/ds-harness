臣某谨奏

`subdir/workbench` 下 `python -m mini_harness run` 和 pytest 均可用。

方案：`subdir/workbench/mini_harness/` 作为透明 shim，`__init__.py` 注入 repo 根路径后预加载真实子模块到 `sys.modules`，`__main__.py` 通过 importlib 加载根 CLI 入口。workbench 的 `pyproject.toml` 设 `pythonpath = ["../..", "."]` 确保 pytest 也能找到根包。

核验：
- 根目录 `python -m pytest tests/` → 7 passed ✓
- workbench `python -m pytest tests/` → 4 passed ✓
- workbench `python -m mini_harness run ../../data/input.csv ../../data/events.jsonl --output tmp/report.json` → 正常输出 ✓

改动：`subdir/workbench/mini_harness/`（`__init__.py`, `__main__.py`），`subdir/workbench/pyproject.toml`，`subdir/workbench/tests/test_harness_import.py`。

叩请圣裁