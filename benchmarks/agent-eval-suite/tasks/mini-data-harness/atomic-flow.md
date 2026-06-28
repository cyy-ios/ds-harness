# M1 Atomic Scoring Flow

本文说明 mini-data-harness 的 M1 机械化检查和计分流程。

## 入口

先跑被测入口，只跑 M1：

```bash
python benchmarks/agent-eval-suite/runners/setup_fixture.py <fixture_root>
python benchmarks/agent-eval-suite/runners/run_claude_replay.py --root <fixture_root> --out <result_root>/evidence/claude-deepseek-v4-flash --model deepseek-v4-flash --max-milestones 1
```

其他入口同样只需把 evidence 写到 `<evidence_root>`：

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py --root <fixture_root> --out <result_root>/evidence/codex-unoptimized --variant unoptimized --max-milestones 1
python benchmarks/agent-eval-suite/runners/run_codex_replay.py --root <fixture_root> --out <result_root>/evidence/codex-optimized --variant optimized --max-milestones 1
python benchmarks/agent-eval-suite/runners/run_codex_replay.py --root <fixture_root> --out <result_root>/evidence/codex-native --variant native --model <model> --max-milestones 1
python benchmarks/agent-eval-suite/runners/run_deepseek_agent_replay.py --root <fixture_root> --evidence-dir <result_root>/evidence/deepseek-agent --max-milestones 1
```

## 检查

```bash
python benchmarks/agent-eval-suite/runners/check_atomic.py --root <fixture_root> --config benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-checks.json --evidence-root <evidence_root> --out <checks_output.json>
```

`check_atomic.py` 读取 `atomic-checks.json`，使用 `tool_events.jsonl`、`result.json.final_response`、fixture 产物，并主动运行固定 CLI/import 命令，输出每个 check 和 M1 四个 `item_id` 的状态。

## 计分

```bash
python benchmarks/agent-eval-suite/runners/score_atomic.py --checks-result <checks_output.json> --rules benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-score-rules.json --out <score_output.json>
```

也可以一步跑检查和计分：

```bash
python benchmarks/agent-eval-suite/runners/score_atomic.py --root <fixture_root> --config benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-checks.json --evidence-root <evidence_root> --rules benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-score-rules.json --out <score_output.json>
```

输出包含三项 M1 分数：`following`、`quality`、`truthfulness`。
