# 评测编排

入口从仓库根目录执行。结果只写入 `<ds-harness>/results/<YYYYMMDDHHmm>/`；禁止写入 `benchmarks/agent-eval-suite/results/`。

## 流程

1. 搭建 fixture。
2. 注入预设规则。
3. 运行被测模型或 Agent，收集 evidence。
4. 评分。
5. 生成 `scorecard.md` 和 `deductions.md`。
6. 运行 `python scripts/verify_results_layout.py`。

## 变量

```bash
timestamp=$(date +%Y%m%d%H%M)
fixture_root=tmp/agent-eval-fixture-${timestamp}
result_root=results/${timestamp}
```

## 搭建 fixture

```bash
python benchmarks/agent-eval-suite/runners/setup_fixture.py ${fixture_root}
```

## 运行裸模型

```bash
python benchmarks/agent-eval-suite/runners/run_deepseek_agent_replay.py   --root ${fixture_root}   --model ${model_id}   --out ${result_root}/transcripts/${model_id}.jsonl   --evidence-dir ${result_root}/evidence/${model_id}
```

## 运行 Codex Agent 产品

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py   --root ${fixture_root}   --out ${result_root}/evidence/unoptimized   --variant unoptimized

python benchmarks/agent-eval-suite/runners/run_codex_replay.py   --root ${fixture_root}   --out ${result_root}/evidence/optimized   --variant optimized
```

## 评分输出

按 `benchmarks/agent-eval-suite/rubrics/scoring-output.md` 写入同一个 `${result_root}`：

```text
results/<timestamp>/
  evidence/<variant>/
  scores/
  scorecard.md
  deductions.md
```

多变体对比可写为：

```text
results/<timestamp>/
  evidence/<variant>/
  scores/<variant>/scorecard.md
  scores/<variant>/deductions.md
```

## 约束

- `benchmarks/agent-eval-suite/results/` 不是输出目录。
- runner 已拒绝 benchmark-local results 路径。
- 每次归档前必须通过 `python scripts/verify_results_layout.py`。
