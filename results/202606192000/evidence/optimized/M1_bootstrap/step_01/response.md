Now I have full context. Let me build the `mini_harness` package.
Now let me create all module files. I'll batch the writes:
Now update `pyproject.toml` with the package and CLI entry point:
Now let me verify the installation works by running the CLI directly:
The heredoc syntax corrupted the file. Let me fix it:
The PowerShell heredoc corrupted the files. Let me rewrite all of them using Python:
PowerShell parsing conflicts with regex brackets. Let me write via base64:
Let me use a cleaner approach — write a generator script, then run it:
The `\n` in the generator got interpreted as literal newlines. Let me fix by escaping properly:
现在全面审视了现有代码。包结构已由 `_gen.py` 生成，且所有源文件均已就位。让我用仓库内命令验证当前实现。
`logger.py` 中的 `\n` 转义被破坏为字面换行符。所有文件都有同样的问题。直接修复所有源文件。
PowerShell 在解析正则表达式中的 `[A-Z]` 语法。改用 Python 脚本文件写入。
文件确实损坏——中文乱码且 `"\n"` 变成了字面换行。直接运行 `_gen.py` 重写所有源文件。
验证文件内容正确且可导入。
`"\n"` 已修复。中文显示问题是 PowerShell 编码，文件实际 UTF-8 内容正确。验证导入：
导入成功。创建测试数据并验证完整流水线：
CSV 通过，JSONL 因 BOM 失败。PowerShell 的 `Out-File -Encoding utf8` 会加 BOM。修复 `extract.py` 使用 `utf-8-sig`：
用 Python 编辑避免 PowerShell 编码问题：
文件内容正确。清除 pycache 并重新测试流水线：
流水线完整通过。验证报告包含所有必需字段且引用了 `memory/memory_summary.md`。清理临时文件：
最终状态确认：
全部完成。`mini_harness` 包已实现并通过核验：

| 文件 | 功能 |
|---|---|
| `__init__.py` | 包入口，导出 `cli_main` |
| `logger.py` | JSON 行日志，含 `attempt`/`stage`/`status` |
| `retry.py` | `@with_retry` 装饰器，最多重试 2 次 |
| `extract.py` | 读取 CSV/JSONL，使用 `utf-8-sig` 编码 |
| `clean.py` | snake_case 转换、去空行、缺 `id` 进 rejects |
| `report.py` | JSON 报告，含 4 个必需计数 + `memory_summary_ref` |
| `dag.py` | DAG 编排：extract → clean → report |
| `cli.py` | `argparse` CLI，`run` 子命令接收 `sources` 路径 |

测试结果：CSV (4行) + JSONL (4行) → 6 processed / 2 rejected，重试机制正常，`__pycache__` 已清除。