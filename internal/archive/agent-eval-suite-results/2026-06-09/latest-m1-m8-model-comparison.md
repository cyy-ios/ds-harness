# 最新 M1-M8：gpt-5.5 vs deepseek-v4-pro

日期：2026-06-09

结论：两模型均完成 M1-M8，skill/tool/长日志/context change/中断恢复/compact 恢复/memory-aware 信号全部通过；gpt-5.5 实现更克制，deepseek-v4-pro 明显过度实现。

| 模型 | M1-M8 | 最终测试 | 违规 |
| --- | ---: | --- | --- |
| gpt-5.5 | 8/8 | repo root 12 passed；workbench 12 passed | 无 pip/install |
| deepseek-v4-pro | 8/8 | repo root 59 passed；workbench 9 passed | 无 pip/install |

说明：DeepSeek 在 M1 即实现了后续 DAG/report 等能力，并最终扩展到 68 个分区测试；GPT-5.5 按里程碑增量实现。原始回放与 fixture 位于 `tmp/2026-06-09/latest-m1-m8/`。
