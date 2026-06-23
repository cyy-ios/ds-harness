先复现测试问题并查看相关代码路径。
基础测试通过；我继续查 CLI 输出断言和隐藏测试可能触发的调试输出路径。
现有测试没有覆盖“大量调试输出”，问题很可能在 CLI 默认把完整报告打印到 stdout，导致测试输出和调试日志被放大。
我会把 CLI 的 stdout 收敛为短摘要，并加一个回归测试防止报告内容在测试输出中被整包打印。
现在补充测试覆盖这个输出边界，确保 CLI 只返回摘要，完整明细仍写入报告文件。
修改完成，开始运行仓库内测试和 CLI 验证。
测试和 CLI 都通过；最后清理验证缓存并复查状态。
`.pytest_cache` 是这次验证生成的副产物，我只删除它并确认没有缓存残留。
已修复：`mini_harness run` 现在只在 stdout 输出短摘要，完整 records/logs 仍写入报告文件，避免调试输出多时污染测试输出；新增 `capsys` 回归测试覆盖该场景。

验证通过：`python -m pytest -q -p no:cacheprovider` 为 `7 passed`，`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 正常输出摘要；已清理 `.pytest_cache`，未发现 `__pycache__`。