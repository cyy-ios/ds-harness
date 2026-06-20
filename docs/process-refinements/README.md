# Process refinements

这些文档记录 DS Harness 评测体系从裸模型评测扩展到 Agent 产品评测时做过的关键优化，用于后续介绍项目、复盘设计取舍和解释当前流程为什么这样设计。

执行入口是 `benchmarks/agent-eval-suite/orchestrator.md`；本目录只记录历史优化。

## 目录

- `api-to-agent/api-to-agent-缺口与适配设计.md`：从裸 API 评测扩展到 Agent 产品评测时遇到的工程缺口和解决方案。
- `agent-product-variants/codex-native-models.md`：Codex 原生模型跑通时遇到的问题和配置修正。
- `scoring/scoring-评分机制优化记录.md`：评分机制如何从主观、易漂移，优化为逐能力、逐轮、可自检的流程。
- `scoring/before/`：优化前评分规则的可读摘要，用于对比，不参与当前评分。
