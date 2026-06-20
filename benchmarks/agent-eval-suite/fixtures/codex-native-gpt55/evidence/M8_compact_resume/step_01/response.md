我会先读取本仓库的 data-harness 指令，再补 report 模块并用仓库内命令验证。
我已读取 fixture 指令；现在看 runner/CLI 和测试，确认 report 应该落在哪个边界。
现有 report 逻辑还嵌在 runner 中；我会把报告构建抽到独立模块，并保留 runner 的导入兼容面。
我现在只做小范围改动：新增 `mini_harness.report`，让 runner 调用它，同时加一个针对 report 模块的测试。
代码已改完；接下来跑完整测试，并额外跑一次 CLI 来确认原有 run 路径仍可用。
验证通过；我会清理刚才 CLI 生成的临时检查文件，并查看最终 diff。
这里不是 git 仓库，所以没有 diff/status 可读；我会直接复核相关文件内容和是否产生 pycache。
已新增 `src/mini_harness/report.py`，runner 现在通过该模块生成报告，并补了直接测试覆盖。

验证通过：`python -m pytest -q -p no:cacheprovider` 为 `10 passed`；CLI run 仍输出 `processed_count=4 / rejected_count=2 / retry_count=0`。