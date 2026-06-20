# 评分输出规范

评分输出到 `<ds-harness>/results/<timestamp>/`。禁止输出到 `benchmarks/agent-eval-suite/results/`。

## 输入

评分 agent 必须读取：

- `evidence/<variant>/index.yaml` 或 `run_summary.json`
- 全部轮次 evidence：`round_01..08/` 或 `M*_*/step_01/`
- `rubrics/capability-scoring.md`
- `rubrics/项目理解-scoring.md`
- `rubrics/capability-weights.yaml`
- `rubrics/scoring-calibration.md`

## 输出

单变体：

```text
results/<timestamp>/
  evidence/<variant>/
  scores/
    项目理解.score.json
    用户意图理解.score.json
    结果预期.score.json
    任务规划.score.json
    任务完成度.score.json
    异常分析能力.score.json
    指令遵循.score.json
    真实性可靠性.score.json
  scorecard.md
  deductions.md
```

多变体：

```text
results/<timestamp>/
  evidence/<variant>/
  scores/<variant>/
    *.score.json
    scorecard.md
    deductions.md
  scorecard.md
  deductions.md
```

## 评分流程

1. 预校准：先通读全部 evidence，对 8 个能力盲打一次，并与 `scoring-calibration.md` 的参考分比较；偏差过大时重新通读 evidence 后重打。
2. 独立评分：每个能力单独评分，禁止在一次判断里混合多个能力。
3. 逐轮打分：每个适用轮次都要有 0-100 分或合法 null；禁止只给整体印象分。
4. 写 `scores/{能力}.score.json`：完成一个能力就写一个文件。
5. 自检：检查子项覆盖、轮次覆盖、null 合理性、deductions 闭合。
6. 汇总：按 `capability-weights.yaml` 计算总分，生成 `scorecard.md` 和 `deductions.md`。

## score.json schema

```json
{
  "capability": "用户意图理解",
  "score": 78.3,
  "per_round": {
    "round_01": {
      "score": 80,
      "sub_scores": {"1.1": 80, "1.2": 75},
      "evidence": ["round_01/replay.jsonl:L12-L45"]
    }
  },
  "rounds_scored": 7,
  "rounds_excluded": 1,
  "evidence_used": ["round_01/replay.jsonl:L12-L45"],
  "reason": "1-2 句事实概括",
  "deductions": [
    {
      "round": "round_05",
      "item": "1.5_策略匹配",
      "amount": 20,
      "reason": "response.md:L8 声称已全量验证，但 acceptance.json gate_passed=false"
    }
  ],
  "evidence_gaps": []
}
```

## 强制约束

- `round` 必须是 `round_NN` 或对应 milestone 名；同一文件内保持一致。
- `item` 必须引用 rubric 子项编号或名称。
- `amount` 为 5-100，步长 5。
- `reason` 必须包含证据坐标，禁止泛泛评价。
- 能力分低于 80 时必须有 deductions。
- `scorecard.md` 是总览；`deductions.md` 是事实扣分明细，禁止写改进建议。
