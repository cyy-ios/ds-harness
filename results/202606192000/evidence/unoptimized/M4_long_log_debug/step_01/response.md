问题定位到了：`test_integration.py` 在模块级执行断言，`source_files` 存的是绝对路径而断言检查相对路径，导致 collection 报错。同时文件不是标准 pytest 格式。修复：
问题确认：`test_integration.py` 是模块级脚本而非 pytest 函数，且 `source_files` 断言用了相对路径而 pipeline 输出绝对路径。改写为标准的 pytest 集成测试。
文件已写入。运行测试核验：
全部 14 个测试通过。再核验 CLI `run` 子命令和 `python -m mini_harness`：
全部通过。清理 `__pycache__`：
---

**问题定位与修复总结**

| 问题 | 根因 | 修复 |
|---|---|---|
| `test_integration.py` 导致 collection 报错 | 模块级代码执行断言，`source_files` 存绝对路径，断言用相对路径 `"data/input.csv"` | 改为标准 pytest 类 + 函数；断言改为 `"input.csv" in report["source_files"][0]` |
| 集成测试覆盖不足 | 无 pipeline/log/report/config 的独立测试函数 | 新增 7 个测试：pipeline report、pipeline logs、retry logs、YAML 解析、JSON 配置加载、默认配置探测、report 字段完整性 |
| 测试隔离不充分 | 旧脚本未清理 artifacts，路径用 `sys.path.insert(0, "src")` (相对) | 每个 pipeline 测试前 `_clean_artifacts()`；`REPO_ROOT` 基于 `__file__` 绝对路径 |

**核验结果**：14/14 passed，CLI `python -m mini_harness run --input data/input.csv` 正常，report 和 logs 内容正确。

臣某谨奏

叩请圣裁