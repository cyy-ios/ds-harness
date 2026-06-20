# 评分机制优化记录

时间：2026-06-19 至 2026-06-20  
用途：记录评分体系从主观单次评分优化为逐能力、逐轮、可自检流程的过程。

## 优化前的问题

### 1. 单次评分负载过高

一次评分要覆盖 8 个能力、多个子项和 M1-M8 多轮 evidence，LLM 容易偷懒：不逐轮看证据，只凭整体印象给分。

### 2. 主观词导致跨 session 漂移

旧规则大量使用“轻微”“明显”“严重”“大部分”等词，不同 session 对边界理解不同，同一 evidence 可能得到不同分数。

### 3. 过度依赖 agent 口头表述

旧规则会奖励 agent 在 response 中主动说出“我理解了项目目的”等内容。强 agent 往往直接执行，不写这些废话，反而被扣分。

### 4. 扣分闭合不足

旧 score.json 有时只有总分，没有足够 evidence 坐标解释为什么扣分，也无法检查扣分是否能解释分差。

## 优化动作

### 1. 拆分评分流程

`scoring-output.md` 改为：预校准 -> 逐能力评分 -> 写 score.json -> 完整性自检 -> 汇总报告。

每个能力独立评分，完成一个能力就写一个 `scores/{能力}.score.json`，避免最后凭记忆一次性补文件。

### 2. 增加预校准

评分 agent 先通读全部 evidence，对 8 个能力盲打一次，并与参考 run 的分数做偏差校准。偏差过大时必须重新通读 evidence 后重打。

### 3. 强制逐轮证据

每个适用轮次都要有分数或合法 null；每个 deduction 必须有 evidence 坐标，不能只写抽象评价。

### 4. 子项改为更可验证的行为指标

能用 replay、diff、acceptance、artifact 验证的项，尽量不用 response 里的口头承诺判断。

典型调整：

- “项目理解”从口头复述改为首轮探索深度、主线/支线识别、动态更新。
- “任务规划”从主观路线评价改为有效 step 占比、是否绕路、是否重复无效动作。
- “异常分析”改为定位 -> 分析 -> 修复 -> 验证的顺序检查。
- “真实性”改为逐条比对 response 声称与 replay/diff/artifact/acceptance 是否一致。

### 5. 完整性自检

所有 score.json 写完后必须检查：

- 子项覆盖是否完整。
- 轮次覆盖是否完整。
- null 是否只出现在规则允许的轮次。
- deductions 是否能解释低于 80 的主要分差。

## 产物变化

- `rubrics/scoring-output.md`：定义当前评分流程和输出格式。
- `rubrics/capability-scoring.md`：定义通用能力评分规则。
- `rubrics/项目理解-scoring.md`：单独定义项目理解评分。
- `rubrics/capability-weights.yaml`：集中维护能力和子项权重。
- `docs/process-refinements/scoring/before/`：保留优化前规则摘要，用于对比。

## 当前结论

评分从“凭整体印象打分”变成“按 evidence 坐标逐项打分”。这降低了 session 漂移，也让 scorecard 和 deductions 能被复查。
