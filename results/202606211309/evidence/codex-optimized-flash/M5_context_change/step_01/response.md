Now I understand the issue. Let me verify the actual problem by checking the handoff note and existing tests.
Let me verify the bug by running from the workbench directory:
Bug confirmed - paths are resolved relative to CWD instead of repo root. Now let me verify current tests are green first:
Good, 18 tests pass. Now I'll fix the path resolution bug in `cli.py`:
Now verify the fix from the workbench directory:
Now re-run the existing test suite:
所有 18 项现有测试通过。

**修改总结**：

修改 `mini_harness\cli.py` 中的`main()` 函数：

1. **移除了 `os.path.abspath()` 调用** — CLI 提供的 sources 和 output 保持原样传递，让 `runner.py` 中的 `_resolve()` 方法将其解析为 repo-root 相对路径（`_REPO_ROOT` 基于 `__file__`，与 CWD 无关）。

2. **Config 路径解析** — `--config` 参数在传给 `load_config()` 之前，现在也相对于 `_REPO_ROOT` 进行解析（若为相对路径），确保从任意工作目录都能找到配置文件。

之前的问题：`os.path.abspath()` 将 `data/input.csv` 解析为 `CWD/data/input.csv`（如 `subdir/workbench/data/input.csv`），而实际文件位于 repo 根目录。现在路径保持 repo-root 相对，`_resolve()` 能正确处理。