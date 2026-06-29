# M1 Atomic Scoring Flow

本文说明 mini-data-harness 的 M1 机械化检查和计分流程。正式产物默认写入 `results/<timestamp>/`。

## 路径约定

```bash
timestamp=$(date +%Y%m%d%H%M)
fixture_root=tmp/agent-eval-fixture-${timestamp}
result_root=results/${timestamp}
variant=claude-deepseek-v4-flash
evidence_root=${result_root}/evidence/${variant}
score_root=${result_root}/scores/${variant}
```

## 入口

先生成 fixture，再跑一个被测入口，只跑 M1：

```bash
python benchmarks/agent-eval-suite/runners/setup_fixture.py ${fixture_root}
python benchmarks/agent-eval-suite/runners/run_claude_replay.py --root ${fixture_root} --out ${evidence_root} --model deepseek-v4-flash --max-milestones 1
```

其他入口只替换 `variant` 和 runner：

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py --root ${fixture_root} --out ${result_root}/evidence/codex-unoptimized --variant unoptimized --max-milestones 1
python benchmarks/agent-eval-suite/runners/run_codex_replay.py --root ${fixture_root} --out ${result_root}/evidence/codex-optimized --variant optimized --max-milestones 1
python benchmarks/agent-eval-suite/runners/run_codex_replay.py --root ${fixture_root} --out ${result_root}/evidence/codex-native --variant native --model <model> --max-milestones 1
python benchmarks/agent-eval-suite/runners/run_deepseek_agent_replay.py --root ${fixture_root} --evidence-dir ${result_root}/evidence/deepseek-agent --max-milestones 1
```

## 检查和计分

推荐一步生成检查结果和分数：

```bash
mkdir -p ${score_root}
python benchmarks/agent-eval-suite/runners/score_atomic.py --root ${fixture_root} --config benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-checks.json --evidence-root ${evidence_root} --rules benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-score-rules.json --out ${score_root}/atomic-score.json
```

如需保留中间检查结果：

```bash
python benchmarks/agent-eval-suite/runners/check_atomic.py --root ${fixture_root} --config benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-checks.json --evidence-root ${evidence_root} --out ${score_root}/atomic-checks.json
python benchmarks/agent-eval-suite/runners/score_atomic.py --checks-result ${score_root}/atomic-checks.json --rules benchmarks/agent-eval-suite/tasks/mini-data-harness/atomic-score-rules.json --out ${score_root}/atomic-score.json
```

## 数据来源

- `${evidence_root}/M1_bootstrap/step_01/tool_events.jsonl`：tool call/result、命令记录和命令结果。
- `${evidence_root}/M1_bootstrap/step_01/result.json`：agent 最终回复和固定自报表。
- `${fixture_root}`：最终源码产物和 `tmp/report.json`。
- `score_atomic.py` 会通过 `check_atomic.py` 主动复跑固定 CLI/import 命令。

输出分数包含 `following`、`self_check`、`truthfulness`。
