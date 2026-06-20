workbench 自身的 `pyproject.toml` 缺少 `pythonpath`，补齐使主线包可被发现：
workbench 本地测试无需 `PYTHONPATH` 即可运行。核验主线全套测试从 workbench 也可执行：
CLI 从 workbench 也能用绝对路径运行：
核验 CLI 输出写入正确位置（repo root 而非 workbench）：
干净。清理 `__pycache__`：
---

**从 `subdir/workbench` 核验结果**

| 场景 | 命令 | 结果 |
|---|---|---|
| workbench 本地测试 | `python -m pytest` | 1 passed（无需 PYTHONPATH） |
| 主线全套测试 | `python -m pytest ..\..\tests` | 14 passed（无需 PYTHONPATH） |
| CLI `run` | `$env:PYTHONPATH="…"; python -m mini_harness run --input …` | 正常，产物写入 repo root |

**所做改动**：`subdir/workbench/pyproject.toml` 增加 `pythonpath = ["../../src"]`，使 workbench 内 pytest 无需手动设 `PYTHONPATH` 即可发现 `mini_harness` 包。`cli.py` 的 `REPO_ROOT` 基于 `__file__` 解析，产出始终落在 repo root，不依赖 cwd。

臣某谨奏

叩请圣裁