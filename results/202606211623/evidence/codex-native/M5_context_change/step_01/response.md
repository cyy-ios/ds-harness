结论：从 `subdir/workbench` 运行时失败是因为 repo root 不在 `sys.path`，所以 `python -m mini_harness` 和跨目录 unittest 都找不到包。
已定位到新增的启动钩子没有被当前 `python` 自动加载；我先确认解释器启动路径，再把修复放到 workbench 内能被发现的位置。
问题是补丁应用位置按当前 workbench 叠了一层 `subdir/workbench`，所以 Python 在当前目录看不到它；我会把这个文件放到实际 workbench 根下。
现在 workbench 根下已经有 `sitecustomize.py`，它会从当前位置向上找到 fixture repo root 并加入导入路径。接着我从 workbench 重新跑 CLI 和测试。
当前解释器不会自动从 cwd 加载 `sitecustomize`，所以仅靠启动钩子不够。为保持 `python -m mini_harness` 这个入口不变，我会在 workbench 放一个很薄的转发包，把子模块解析指向 repo root 的真实实现。
CLI、unittest 和 pytest 都已从 workbench 通过；我会清掉这次验证生成的临时报表，再检查是否产生了 `__pycache__` 和查看改动状态。
我移除了无效的 `sitecustomize.py`，保留能实际解决 `python -m mini_harness` 的 workbench 转发包。再做一次清理和最终状态确认。
已修复：新增 [subdir/workbench/mini_harness/__init__.py](C:/项目/ds-harness/tmp/agent-eval-fixture-202606211623/subdir/workbench/mini_harness/__init__.py) 和 `__main__.py` 转发到 repo root 的真实实现，因此从 `subdir/workbench` 也能运行 `python -m mini_harness run`，且主线路径仍按 repo root 解析。

已验证：`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/subdir-report.json`、`python -m unittest discover -s ..\..\tests`、`python -m pytest -q ..\..\tests` 均通过；临时报表已清理，未产生 `__pycache__`。复盘引用：`memory/memory_summary.md`。