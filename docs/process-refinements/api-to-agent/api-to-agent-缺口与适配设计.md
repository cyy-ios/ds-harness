# 从 API 评测扩展到 Agent 产品评测的缺口与适配

## 背景

Agent Eval Suite 最早按“裸模型 API + 简单工具循环”设计。扩展到 Codex 这类 Agent 产品后，评测对象从一个 HTTP 模型调用变成一个带会话、工具、权限、压缩和本地状态的产品运行时，因此需要重新处理执行、证据和评分边界。

## 缺口 1：逐轮 CLI 调用会丢失同一 session 上下文

裸模型 runner 可以自己维护 messages；Agent 产品若每轮重新执行 CLI，会变成全新会话，M1 产生的文件和上下文无法在 M2-M8 中延续。

解决：Codex 首轮用 `codex exec --json` 获取 `thread_id`，后续轮次用 `codex exec resume <thread_id>` 继续同一 thread。

## 缺口 2：持久规则注入方式不同

裸模型可以把规则直接放进 system prompt；Agent 产品通常通过项目文件加载规则，例如 Codex 的 `.codex/instructions.md` 和 `.codex/config.toml`。

解决：写 `inject-persistent-rules.md`，按被测产品的加载机制注入和还原规则；Codex 侧统一使用正确的 `config.toml` 层级和 `instructions.md` 相对路径。

## 缺口 3：工具集合规模不同

裸模型 runner 只暴露少量模拟工具；Agent 产品自带完整工具集。直接比较“工具选择能力”会把 harness 差异误当成模型能力差异。

解决：不把“工具选择”作为跨产品独立能力；只作为任务完成度、任务规划和真实性的证据之一。

## 缺口 4：Agent 产品证据格式不统一

裸模型 runner 可以在每个 tool step 旁路收集统一 replay；Codex 输出的是产品原生 JSONL 事件。

解决：保留产品原生输出，同时归一到评分可读的 evidence 结构。评分 agent 必须兼容裸模型的 `round_01..08` 和 Codex 的 `M*_*/step_01` 两种目录形态。

## 缺口 5：上下文压缩触发不可完全控制

裸模型不会自动 compact；Agent 产品可能自动压缩，但压缩位置受运行时影响。

解决：Codex runner 设置 `model_auto_compact_token_limit`，尽量让压缩在 M7/M8 附近触发；评分时把 compact 事件作为 evidence，不把压缩位置异常直接算成被测模型错误。

## 缺口 6：主控环境的安全策略会拦截被测 Agent

为了非交互跑完 M1-M8，被测 Codex 需要 `approval_policy=never`、`danger-full-access` 和 `--skip-git-repo-check`。主控环境可能把这个组合判断为高风险。

解决：只在隔离 fixture 内运行，并在主控权限配置中显式允许这条被测命令；同时禁止把密钥和 fixture 外产物写入公开结果。

## 缺口 7：参考答案不能暴露给被测 Agent

评测方的 rubric、验收脚本、历史结果不能放进被测 agent 可见路径，否则测试失效。

解决：fixture 只包含自然任务材料；评测脚本和 scoring rubric 留在主仓库 runner/rubrics 下，由主控流程在任务结束后读取。

## 当前落地

4 条运行路径统一收敛到 `orchestrator.md`：裸模型、Codex 未适配、Codex 已适配、Codex 原生模型。所有路径都输出到 `results/<timestamp>/evidence/<variant>/`，再交给同一套评分规范。
