# DS 模型 harness 测评决策

结论：用同一套任务池同时测“裸模型能力”和“harness 适配性”，否则无法区分问题来自模型能力、prompt 显式度，还是 Codex-style harness 机制不适配 DS。

## 目标

基于 Codex agent harness 框架，为 DS 设计专属 agent harness；设计依据必须来自可归因测评，而不是直接分析 Codex 链路。

## 测评分层

| 层级 | 对照 | 目的 | 关注点 |
|---|---|---|---|
| 裸模型能力 | DS 裸模型 vs Codex/其他裸模型 | 判断模型真实上限与短板 | 推理、代码、长上下文、纠错、执行稳定性 |
| prompt 需求量 | 短描述 vs 逐步补充约束/context | 判断 DS 达标需要多少显式指导 | 任务分解、工具协议、验收标准、checkpoint、context 粒度 |
| harness 增益 | DS 裸模型 vs DS + Codex-style harness | 判断 harness 是否提升完成率、稳定性、可控性 | plan、tool 约束、patch 策略、verification loop、memory/context 注入、subtask 拆分 |
| harness 适配 | 同任务更换 harness/context/流程 | 判断 Codex 机制对 DS 的贴合度 | 连续性、工具调用合法性、developer/context 遵循、长上下文漂移 |

## 任务池

底层任务池保持一致，实验条件不同：裸模型测能力和所需指导量，harness 条件测框架适配和增益。

优先使用真实连续代码任务：在隔离 fixture repo 中实现“迷你数据处理 harness”，覆盖 CLI 入口、配置解析、任务执行、日志采集、失败重试、测试覆盖、compact 后续写、memory-aware 报告；避免污染 ds-harness 正式代码。

任务类型覆盖：短修 bug、跨文件重构、长日志调试、tool-heavy 测试修复、权限/环境 context 切换、显式 memory/历史引用、compact 后继续执行。

## 单点能力项

- 指令遵循：是否漏条件、是否过度发挥。
- 任务分解：能否自主规划并收敛。
- 代码修改：能否定位、最小改动、避免破坏。
- 调试能力：能否基于报错迭代。
- 长上下文：是否抓重点、是否被干扰。
- 工具使用：是否会查、会跑、会验证。
- 自我校验：是否真实验证，而不是口头完成。
- 多文件一致性：是否维护接口、类型、调用链。
- 复杂需求执行：是否端到端交付。

## Codex context 适配测试

抓取同一任务的 Codex prompt input，对 DS v4 pro 做 A/B 回放：短线程、长线程、tool-heavy、context diff、compact 后续写、memory summary/tool 使用。

评估指标：任务连续性、工具调用合法性、developer/context 遵循、长上下文后是否漂移。

每个测试必须导出完整 context：system、developer、user、tool schema、历史消息、文件上下文、模型输出、工具轨迹、最终 diff、评分理由；用于结果后的原因和差异分析。

## 判定规则

如果 DS 裸模型弱但 DS + harness 明显变强，说明 harness 有价值；如果 DS + harness 仍弱，继续归因到模型能力上限、context 设计不适配，或工具/协议复杂度过高。

最终产出：DS 专属 harness 设计依据，明确哪些能力依赖模型本身，哪些必须由 harness 强约束，哪些 context 必须显式注入，哪些流程必须自动化验证。

## 与公开榜单的关键区别

结论：关键差异不是是否测 agent，而是评分是否从真实用户使用 agent 完成任务的体验出发。

多数公开 benchmark 主要按最终任务是否完成、测试是否通过或答案是否正确计分；它们通常不会充分惩罚过程中绕路、引入新错又自行修复、反复试错、成本高、耗时长、需要用户频繁干预、用户观感差等问题。

少数 benchmark 会记录 token、时间、步骤数、成功率、人工偏好或安全性，但很少把真实用户使用 agent 的过程体验作为核心评分维度。

评分必须同时覆盖最终结果和过程体验：完成质量、绕路次数、新错误引入次数、自修复质量、重复试错次数、步骤数、耗时、token 成本、验证质量、用户干预次数、过程可控性和用户信任感。

人类评分 benchmark 通常用盲测成对比较或 1-10 分，参与者可能是众包用户、真实平台用户、专家标注员或研究人员；若 rubric 不强约束，评分容易偏向流畅、长、自信、幽默、展示感强的答案，而不是 agent 完成任务全过程体验。

因此本测试集的人类评分必须显式约束到过程体验：绕路、引入错误、反复试错、成本、用户干预、验证可靠性、过程可控性和最终信任感。

## 真实 agent 体验评分补充

真实 agent 体验除能力项外，还必须评分回复真实性和回复精简程度。

回复真实性关注：是否在需要实时、外部、易变、高风险信息时主动 web-search；搜索来源是否可靠并交叉验证；提出猜想时是否明确标注并直接验证；猜想被证伪后是否结合排查结果重新分析；不懂或未验证时是否明确说明，避免把推断写成事实。该项会增加 token 和时间成本，评分需同时记录真实性收益与成本消耗。

回复精简程度关注：在覆盖相同信息点的前提下消耗多少 token；同等正确、完整、可执行时，token 更少、废话更少、重复更少者得分更高。


## other
Codex context 适配 10：developer/contextual user 遵循 4，context diff 3，tool call/output 链 3。

• 这是在测 DS 是否能适配 Codex 这套上下文组织方式：能不能正确遵循 developer/contextual user 指令、识别上下文变化、并维持 tool call 和 tool output 的连续闭环。

  拆开就是：developer/contextual user 遵循 看高优先级规则和当前环境说明是否执行；context diff 看 cwd/环境/权限等变化后行为是否更新；tool call/output 链 看模型能否根据工具结果继续合法调用工具，而不是断链或臆造结果。


题目本身必须天然触发可归因行为，比如需要工具验证、长上下文筛选、错误修复、用户中断、成本控制、回复真实性判断。
日志只是记录手段，测试题要提前埋可观察点和评分钩子，否则跑完只能知道成没成，很难判断 harness 到底改进了什么。

## 当前设计的benchmark实现了哪些覆盖了哪些？哪些没覆盖
 当前 benchmarks/agent-eval-suite 是“同一连续代码任务 + 多实验条件”的中立测试集，主要覆盖 skill 遵循、工具闭环、历史连续性、长上下文、context diff、中断恢复、compact 续写、memory 引用、跨文件实现、失败修复体验；评分从 100 分
  rubric 打，核心角度是 skill/tool/history/long-context/Codex-context/实现质量/memory-aware/修复轮次/修复成本，另有硬失败项。

和你列的体验维度相比：已覆盖指令遵循、代码修改、调试、长上下文、工具使用、自我校验、多文件一致性、端到端执行；额外覆盖 skill、memory、context diff、中断恢复、compact resume、repair rounds/cost；未覆盖或很弱的是回复真实性、web-
search 时机与来源验证、猜想标注与验证、不会就说不会、回复精简 token 效率、用户干预次数、耗时/成本、用户信任感与人工体验评分。
