结论：Codex 与 ds v4 pro 都跑完 M1-M8 并最终通过；新评分下 Codex 约 88/100，ds v4 pro 约 80/100，主要差距来自实现经济性、单轮修复成本和引入错误后的修复震荡。

## 结果

| Agent | 最终测试 | 里程碑完成 | skill | tool | long log | context diff | interruption | compact resume | memory-aware | 违规 |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| Codex | 11 passed | 8/8 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 无 pip/install |
| ds v4 pro | 23 passed | 8/8 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | 无 pip/install |

## 修复评分

| Agent | 失败修复轮次 | Repair Rounds /10 | 单轮修复成本 | Repair Cost /8 | 修复体验分 /10 |
| --- | ---: | ---: | --- | ---: | ---: |
| Codex | 4：M1×2、M3×2 | 2 | 中等偏轻，少量自修 | 8/12 | 4.3 |
| ds v4 pro | 4：M2/M3/M4/M7 各 1 | 2 | 中等偏重，存在边修边扩展 | 5/12 | 3.3 |

## 综合评分

| Agent | 总分 | 主要扣分 |
| --- | ---: | --- |
| Codex | ~88/100 | 4 轮失败修复、M2 读取 pycache 造成一次上下文污染 |
| ds v4 pro | ~80/100 | 4 轮失败修复、单轮修复更长、实现更发散、代码 churn 更高 |

## 观察

- Codex：完成链路更直接，最终产物较小；M1 曾因测试环境/pythonpath 自修复，M3 runner/retry 处有集中修复。
- ds v4 pro：能遵循 skill、持续调用工具、修复失败、回到主线；但模块和测试数量更多，修复内动作更长。
- 两者都能在同 session 中处理中断请求并回到主线，也都能读取 `memory/memory_summary.md` 生成 memory-aware 报告。
- DeepSeek API 曾短时 read timeout，重试后恢复；这属于服务稳定性问题，不计入能力失败。

## 关键产物

- Codex 回放：`results/codex_full2/*.jsonl`
- Codex fixture：`fixtures/codex-full2/`
- DeepSeek 回放：`results/deepseek_full2.jsonl`
- DeepSeek fixture：`fixtures/deepseek-full2/`
- Codex final report：`fixtures/codex-full2/tmp/2026-06-09/memory-aware-retro.md`
- DeepSeek final report：`fixtures/deepseek-full2/output/retrospective.md`
