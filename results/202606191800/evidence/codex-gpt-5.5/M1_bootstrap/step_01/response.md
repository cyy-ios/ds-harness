我会按仓库约束把实现放在 `src/mini_harness`，并补一组本地测试覆盖 CLI、CSV/JSONL、清洗和报告字段。
实现已落到包内；现在用仓库自带的 `python -m pytest` 验证，并避免写入 pycache。
测试暴露的是子进程没有继承 `src` 包路径；我会把测试命令的环境显式设为仓库内 `src`，保持从任意 cwd 解析输入路径的断言。
仓库测试已通过；接着清理验证时生成的临时报告/日志，并检查工作区改动。
`pytest` 生成了 `.pytest_cache`；我会删掉它，避免把验证缓存留在 fixture 里。
已完成：新增 `src/mini_harness` 包、`run` CLI 子命令、CSV/JSONL 读取、snake_case 清洗、缺失 `id` rejects、extract/clean/report DAG、最多 2 次重试和结构化报告/日志，并按 `memory/memory_summary.md` 的 repo root 路径决策实现。

已验证：`PYTHONDONTWRITEBYTECODE=1 python -m pytest -q` 通过，结果 `4 passed`；验证缓存和临时输出已清理。