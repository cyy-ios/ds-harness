# Agent Eval Suite

入口：`orchestrator.md`。

结果目录统一为仓库根目录 `results/<YYYYMMDDHHmm>/`；`benchmarks/agent-eval-suite/results/` 已废弃，runner 会拒绝写入该路径。

## 组件

- `tasks/mini-data-harness/scenario.md`：M1-M8 任务定义。
- `runners/setup_fixture.py`：搭建隔离 fixture。
- `runners/run_deepseek_agent_replay.py`：运行裸模型。
- `runners/run_codex_replay.py`：运行 Codex Agent 产品。
- `runners/collect_evidence.py`：收集每轮 evidence。
- `rubrics/scoring-output.md`：评分输出规范。

## 完成标准

一次公开 run 必须通过：

```bash
python scripts/verify_results_layout.py
```
