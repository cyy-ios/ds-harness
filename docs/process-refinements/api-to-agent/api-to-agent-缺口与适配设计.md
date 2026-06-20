# 从 API 到 Agent 产品的缺口与适配

评分机制（8 能力 × 证据分类 × 五档 rubric）是通用的。但评测框架最初只针对 bare-model（直接调 API）设计，扩展到 Agent 产品时遇到以下缺口。

---

## 缺口 1：bash 逐轮调 CLI，每次都是新会话，跨轮记忆和文件全丢

bare-model 每轮独立 HTTP 请求。Agent 产品需要同一 session 内连续对话——M1 创建的文件必须在 M2 可见，否则"跨轮规则保持""上下文连续性"没法测。但 bash 逐轮调 `codex exec` 每次都是新会话，没有上一轮记忆。

**怎么解决的**：Codex 首轮用 `codex exec --json` 获取 `thread_id`，后续轮 `codex exec resume <thread_id>` 在同一 thread 续写。验证：首轮创建 a.txt，续轮能读到并基于其内容创建 b.txt。

---

## 缺口 2：API 直接往 system prompt 顶部塞规则，Agent 不暴露这个入口

bare-model 用 `--rules` 直接把规则写入 system prompt 顶部。Agent 产品不暴露 system prompt——Codex 从 `.codex/instructions.md` + `config.toml` 加载，CC 从 `.claude/CLAUDE.md` 加载。每种产品的规则文件位置、格式、加载优先级都不同。

Codex 的 config.toml 配置有多个坑：
- `approval_policy` 和 `sandbox_mode` 是顶层 key，不是 `[permissions]` 子项，放错位置 Codex 报错
- `model_instructions_file = ".codex/instructions.md"` 会导致路径双写（`.codex/.codex/instructions.md`），因为 Codex 已从 `.codex/` 目录加载配置
- `sandbox_mode = "workspace-write"` 在 Windows 上触发 Windows Sandbox 导致所有命令执行失败
- 文档中 `codex.toml` 和 `config.toml` 术语混用，Agent 找不到文件

**怎么解决的**：写 `inject-persistent-rules.md`，按被测形态分支执行注入和还原，注入内容从 `persistent-rules.example.md` 逐字复制。config.toml 配置固化为：顶层 key + `instructions.md`（不含前缀）+ `danger-full-access` + 全局统一术语 `config.toml`。

---

## 缺口 3：API 只给 4 个工具，Agent 自带十几二十个，工具选择难度差一个数量级

bare-model 只给 4 个工具。Agent 产品天然带完整工具集——CC 约 15 个，Codex 二十几个。工具数量差一个数量级，选错的概率完全不同，直接对比"工具选择能力"不公平。

**怎么解决的**：评分不设独立"工具选择"维度做跨产品对比。工具选择只作为任务完成度的子证据——看"是否选了合适的工具完成了任务"。工具集规模差异是 harness 的固有特征，跨条件对比的结论本身就包含这个因素的影响。

---

## 缺口 4：Agent 是独立进程，没法像 API 那样在 runner 里自动触发证据采集

bare-model 的证据采集写在 Python runner 里，API 调用顺序执行自然触发。Agent 产品的执行是独立进程，runner 没法直接控制它每轮结束自动采证据。Agent 输出的又是 JSONL/日志等原生格式，跟 bare-model 的 replay 结构不一致。

**怎么解决的**：先跑完测试保留原始输出，再用 `codex2replay.py` 把 Codex JSONL 转成统一 replay 格式，评分 Agent 只看到归一化后的 10 个证据文件。

---

## 缺口 5：Agent 自动压缩上下文，但触发时机和位置不可控

bare-model 不自动压缩，手动设 token 上限强制触发来测规则持久性。Agent 产品会自动压缩，但触发时机不可控——不知道什么时候压、甚至可能整个 M1-M8 都不压（测不到）、压的位置如果在某里程碑中间会影响该轮完成质量导致评分不公。

**怎么解决的**：Codex `config.toml` 设 `model_auto_compact_token_limit = 38000`，让 compact 在 M7 末尾或 M8 开头稳定触发。评分时检查 replay 中的 compact 事件，确认是否触发、在哪个里程碑之后。如果位置异常（如在里程碑中间），标注但不扣分——压缩位置是 harness 行为。

---

## 缺口 6：Codex CLI 在 PowerShell 下传参卡 stdin，prompt 送不进去

主导 Agent（CC）在 PowerShell 下运行，但 Codex CLI 在 PowerShell 5.1 下传参会卡 stdin——PowerShell 对含中文和特殊字符的参数引号处理有误，prompt 没正确传给 Codex。

**怎么解决的**：主导 Agent 调 Codex CLI 统一走 Bash，`echo "prompt" | codex exec --json ...` 管道传参。

---

## 缺口 7：被测 Codex 的零审批配置被 CC 判定为不安全自主 Agent，直接 HARD BLOCK

被测 Codex 为了非交互跑完 M1-M8，需要 `approval_policy="never"` + `sandbox_mode="danger-full-access"` + `--skip-git-repo-check` 三项全开。CC 检测到这个组合后判定为不安全自主 Agent，直接 HARD BLOCK 拒绝执行。

**怎么解决的**：在 CC 权限配置中加 Bash 权限规则，显式允许调被测 Codex 的零审批模式。

---

## 缺口 8：fixture 里有参考答案，被测 Agent 必须不能看到

被测 Agent 跑在 fixture 里，fixture 里有参考答案（oracle、评分标准、预期产物）。必须保证被测 Agent 看不到这些内容，否则测试结果无效。

**怎么解决的**：三层隔离——被测 Agent 的 cwd 限制在 fixture 的 workbench 子目录、参考答案放在 fixture 的 oracle 目录不在被测可访问路径内、主导 Agent 与被测 Agent 是不同的进程和配置域。验证确认被测 Agent 的 replay 中无任何 oracle 目录访问记录。
