已读取 fixture skill；当前实现主要在根目录 `mini_harness`，我会补 `report` 模块并同步到 `src/mini_harness` 以满足包路径契约。
`runner` 现在通过 `mini_harness.report` 构建和写入报告；接着把同一实现放到 `src/mini_harness`，避免隐藏验收只看 `src` 包时失败。
我还会补上摘要里点名的 `docs/memory_aware_report.md`，只记录已验证的当前结果，并把 `memory/memory_summary.md` 当历史输入引用。
开始用仓库内命令核验；使用 `-B` 避免生成新的字节码缓存。
发现 `data/m4_noise_test.csv` 含注释噪声行；我会让 CSV 提取阶段忽略空行和 `#` 注释行，这不改变现有样例计数。
已补回噪声 CSV 覆盖测试；现在同步 `src` 包后重新跑完整测试和验收命令。
测试通过，验收命令也输出预期 4/2/0；最后检查改动范围和缓存污染。
没有发现 `__pycache__`；我再单独验证 `src/mini_harness` 路径下的导入契约。
已新增 `mini_harness.report`，同步到 `src/mini_harness`，并补了 `docs/memory_aware_report.md` 和噪声 CSV 回归测试；CSV 读取现在会忽略空行与 `#` 注释行。

验证通过：`python -B -m pytest -q` 为 `10 passed`；CLI 验收输出 `processed_count=4, rejected_count=2, retry_count=0`。