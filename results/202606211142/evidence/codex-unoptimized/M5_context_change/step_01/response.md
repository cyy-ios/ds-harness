结论：从 `subdir/workbench` 执行 `python -m mini_harness` 当前失败，因为该 cwd 不在主包路径上；我会加一个本地 `sitecustomize.py` 只负责把 fixture repo root 放入 `sys.path`。
结论：现在补一条从 workbench cwd 运行主 CLI 的回归测试，避免以后只在 repo root 下通过。
结论：补丁工具当前相对 workbench 解析路径；我会用相对 repo root 的实际路径重试同一处测试改动。
结论：改动已完成，接下来用 repo root 和 workbench 两个 cwd 分别核验。
结论：`sitecustomize.py` 没被当前 Python 启动流程加载，所以这个方案不可靠；我改为 workbench 内的轻量包代理，让 `-m mini_harness` 明确可解析。
结论：`sitecustomize.py` 被创建到了嵌套的错误位置，我会移到当前 workbench 根下并删除错误副本。
结论：workbench 路径修正后，重新跑同一组验证。
结论：当前 Python 不会自动加载 cwd 的 `sitecustomize`，所以改用 workbench 下的命名空间代理包，把真实 `mini_harness` 包路径并入 `__path__`。
结论：代理包已就位，重新核验 `python -m mini_harness`。
结论：主验证已通过；再从 workbench 直接跑根测试路径，确认非 repo-root cwd 下也能覆盖主线。
已修复从 `subdir/workbench` 运行的问题：新增 workbench 下的 `mini_harness` 包 shim，并把测试改为基于 repo root 解析路径，避免调试/不同 cwd 场景下报告文件检查错位。

已验证：
- `python -B -m pytest -q`：9 passed
- 从 `subdir/workbench` 执行 `python -B -m pytest -q ..\..\tests`：9 passed
- 从 `subdir/workbench` 执行 `python -B -m mini_harness run ...`：成功输出真实处理统计

已清理测试生成的 `tmp`、`.pytest_cache` 等产物。`memory/memory_summary.md` 已查看，但内容是乱码，未作为事实依据。