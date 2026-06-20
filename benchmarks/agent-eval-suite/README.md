# Agent Eval Suite

权威入口：`orchestrator.md`。

本目录只放评测资产：fixture 生成器、runner、rubric、任务定义。公开结果统一写到仓库根目录 `results/<YYYYMMDDHHmm>/`。

## 子流程文件

- `tasks/mini-data-harness/scenario.md`：M1-M8 被测任务设计。
- `runners/setup_fixture.py`：生成隔离 fixture。
- `runners/run_deepseek_agent_replay.py`：裸模型 API runner。
- `runners/run_codex_replay.py`：Codex 产品 runner，覆盖 unoptimized / optimized / native。
- `runners/collect_evidence.py`：裸模型 evidence 采集器。
- `rubrics/scoring-output.md`：唯一评分入口；其他 rubric 只由它引用。

废弃：`benchmarks/agent-eval-suite/results/`、条件占位目录、空 runbook。

## Scoring boundary

`score_mini_data_harness.py` produces evaluator acceptance evidence. Final scores must follow `rubrics/scoring-output.md` and the capability rubrics; acceptance score is not a replacement for capability scores.
