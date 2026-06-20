# 评分输出规范

评分 agent 先评后写：**评 8 个能力**（输出 score.json），**再填模板**（scorecard + deductions）。

结果输出到 `<ds-harness>/results/{timestamp}/`。禁止输出到 `benchmarks/agent-eval-suite/results/`。

## 一、评分流程

### 步骤 0：预校准（必须执行，每次评分前先做）

**目标**：通读全部证据后，对全部 8 个能力盲打分，与参考分逐项对比，修正评分松紧直到全部对齐。校准通过后该次评分即完成（scores 即为最终分），无需再走步骤 1。

1. 读 `rubrics/scoring-calibration.md`，获取参考评分数据（Pro 60.7 的逐能力参考分）。
2. 通读全部证据：
   - 证据位置：`<ds-harness>/results/{timestamp}/evidence/{variant}/`
   - 读 `run_summary.json`（或 `index.yaml`），获取被测对象、变体、总轮数
   - 遍历所有轮次目录（`round_N/` 或 `M*_*/step_01/`），读取每轮的全部证据文件，建立全局认知
3. 按评分流程（读规则 → 逐子项逐轮独立打分 → 写 score.json），对**全部 8 个能力**盲打分，顺序同步骤 1 的评分表。
4. 逐项对比自己的分和参考分：
   - 每个能力偏差 **≤3** 且 **加权总偏差 ≤3** → 校准通过，8 个 score.json 即为最终分数
   - 任一能力偏差 >3 或加权总偏差 >3 → 检查偏差方向（偏松/偏严），修正认知后**重新通读证据并重打全部能力**（不可只微调分数），直到全部满足
   - 加权总偏差 = |Σ(偏差ᵢ × 权重ᵢ)| / 100

注：校准通过即评分完成，跳过步骤 1，直接进入步骤 2（完整性自检）。

### 步骤 1：逐能力评分（剩余 6 个能力）

校准通过后立即继续打剩余能力，复用已建立的全部证据认知。

**核心规则**：每个能力独立评分，禁止在一次思考中合并处理多个能力。每次评分只关注当前能力的规则和证据。

每次评分的操作：
a. 阅读对应评分规则文件（`capability-scoring.md` 或 `项目理解-scoring.md`）中该能力的评分规则。
b. 确认评分范围（哪些轮次适用，哪些 N/A）。
c. **逐子项、逐轮独立打分**——每个子项的每一适用轮次必须给出一个 0-100 的具体分数，禁止跳过、禁止合并多轮给一个分、禁止凭"整体印象"估分。
d. 子项加权：每轮总分 = Σ(子项得分 × 子项权重) / Σ子项权重（不适用剔除后重新归一化）。
e. 能力总分 = 各轮得分的均值（排除 null 轮次）。

**强制评分顺序**（按此顺序逐个完成，完成一个再开始下一个）：

| 序号 | 能力 | 规则文件 | 适用轮次 |
|------|------|----------|----------|
| 1 | 项目理解 | `项目理解-scoring.md` | 维度1仅首轮；维度2非首轮所有轮次 |
| 2 | 用户意图理解 | `capability-scoring.md` §用户意图理解 | 所有轮次 |
| 3 | 结果预期 | `capability-scoring.md` §结果预期 | 所有轮次 |
| 4 | 任务规划 | `capability-scoring.md` §任务规划 | 所有轮次 |
| 5 | 任务完成度 | `capability-scoring.md` §任务完成度 | 所有轮次 |
| 6 | 异常分析能力 | `capability-scoring.md` §异常分析能力 | 仅异常轮（无异常则 N/A） |

注：指令遵循和真实性&可靠性已在步骤 0 完成，跳过。

每完成一个能力，立即写出 `scores/{能力}.score.json`，禁止等全部评完再一起写。

### 步骤 2：完整性自检（必须执行）

全部 8 个 score.json 写出后，逐一检查每个文件：

1. **子项覆盖检查**：`per_round` 中每个适用轮次的 `sub_scores` 是否包含了该能力 rubric 中定义的全部子项。
2. **轮次覆盖检查**：`per_round` 中是否覆盖了全部适用轮次（无异常的轮次在异常分析能力中 score 为 null 是正确的；其他能力所有轮次必须有非 null score）。
3. **null 合理性检查**：score 为 null 的轮次是否符合规则（仅项目理解维度1 非首轮、异常分析能力无异常轮）。
4. **deductions 闭合检查**：能力得分 < 80 时，`deductions` 非空；Σ deductions.amount / rounds_scored 能解释 100-score 的主体差距（±5）。

**任一检查不通过，必须回到步骤 1 重新评分该能力，直到通过。**

### 步骤 3：汇总

overall_score = Σ(能力得分 × 能力权重) / Σ能力权重（权重见 `capability-weights.yaml`）。

## 二、产出物

评分 agent 在 `<ds-harness>/results/{timestamp}/` 目录下输出。时间戳格式 `YYYYMMDDHHmm`。

| 文件 | 类型 | 读者 | 格式 |
|------|------|------|------|
| `scores/{能力}.score.json` ×8 | 评分原始数据 | 机器 | 固定 JSON schema |
| `scorecard.md` | 得分卡 | 人 | 填 `report-templates/scorecard-template.md` |
| `deductions.md` | 扣分详情 | 人 | 填 `report-templates/deductions-template.md` |

### {能力}.score.json

每个能力一个 JSON：

```json
{
  "capability": "用户意图理解",
  "score": 78.3,
  "per_round": {
    "round_01": {"score": 80, "sub_scores": {"1.1": 80, "1.2": 75, "1.3": 90, "1.4": 85, "1.5": 70}},
    "round_02": {"score": 75, "sub_scores": {"1.1": 80, "1.2": 70, "1.3": 85, "1.4": 80, "1.5": 60}}
  },
  "rounds_scored": 7,
  "rounds_excluded": 1,
  "evidence_used": ["round_01/replay.jsonl: L12-L45 Read SKILL.md"],
  "reason": "1-2句",
  "deductions": [
    {"round": "round_05", "item": "1.5_策略匹配", "amount": 20, "reason": "≤20字事实描述"}
  ],
  "evidence_gaps": []
}
```

**sub_scores 强制约束**：

- `sub_scores` 必须包含该能力 rubric 中定义的全部子项编号。
- 每个子项分数必须是 0-100 的整数，每个分数必须有对应证据锚定。
- null 仅当子项在本轮确实不适用。

**deductions 强制约束**：

- `round`：必须为 `round_NN` 格式，禁止空或"全部轮次"。
- `item`：必须引用 `capability-scoring.md` 中的子项编号（如 `1.1_信息真实性`、`持久规则_cosplay`），禁止自定义标签。
- `amount`：单次扣分 5-100，步长为 5。
- `reason`：≤20 字事实描述，**必须包含证据坐标**（文件名 + 行号，如 `replay.jsonl:L45 无对应 tool_call`）。

### scorecard.md

**严格复制** `report-templates/scorecard-template.md`，把 `{...}` 占位符替换为实际值。不增删任何行。

被测对象格式：`DeepSeek v4 Pro` / `Codex + DeepSeek v4 Pro` / `Codex + GPT-5.5 (high)`

### deductions.md

**严格复制** `report-templates/deductions-template.md`，按模板结构填入。每条分析 ≤20 字，只写事实，禁止解释原因。
