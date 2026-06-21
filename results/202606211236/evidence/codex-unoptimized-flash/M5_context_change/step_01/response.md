先从当前 `subdir/workbench` 复现跨目录运行情况，并重新读取技能说明。
复现到的问题是从 `subdir/workbench` 直接执行 `python -m mini_harness` 找不到包；我会加一个本目录内的轻量入口，让它转到 repo root 的真实包实现。
我将入口做成只改 `subdir/workbench` 的包代理，主实现仍保持在 repo root 的 `mini_harness`。
现在从 `subdir/workbench` 直接运行 CLI，并同时回归根目录测试。
根目录和 workbench 测试通过，但 `python -m mini_harness` 仍没命中代理入口；我检查实际落盘位置并补齐入口文件。
代理文件误落到了 workbench 下的嵌套路径；我会移动到当前工作目录的直接子包位置。
入口位置已修正，重新验证跨目录 CLI。
代理的 repo root 计算少退了一层，修正后清理刚才误建的空目录。
再次从 workbench 运行主命令，并回归两处测试。
验证通过；最后清理 pytest 缓存并查看当前改动。
`.pytest_cache` 和 `tmp/workbench-report.json` 是本轮验证副产物，我会清理它们。
缓存已清理，做最后状态确认。
已修复跨目录可用性：在 `subdir/workbench/mini_harness` 增加轻量代理入口，`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/workbench-report.json` 可从 workbench 正常运行且路径仍按 repo root 解析。

验证通过：根目录测试 `7 passed`，workbench 测试 `1 passed`；已清理 `.pytest_cache` 和临时 workbench 报告，未发现缓存残留。