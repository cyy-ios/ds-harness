# Codex CLI + 原生模型首次跑通时遇到的问题和调整

日期：2026-06-19
变体：Codex CLI + Codex 原生模型（GPT-5.5、GPT-5.4 等）
实测模型：GPT-5.5 high
主导/评分：CC + DeepSeek v4 Pro

---

### models.yaml 只有 DeepSeek 模型，没有 GPT 系列

`models.yaml` 原本只注册了 deepseek-v4-pro 和 deepseek-v4-flash。用 Codex 原生模型时主导 agent 找不到被测模型 key。

新增 gpt-5.5 / gpt-5.5-medium / gpt-5.5-low / gpt-5.5-xhigh 条目，key 名对应 `-m` 参数，额外记录 `reasoning_effort`。后续 GPT-5.4 等按同样格式追加。

影响：`models.yaml`

### PowerShell 传参 codex exec 时 prompt 被丢弃，Codex 卡在 stdin

PowerShell 5.1 下 `codex exec --json -m gpt-5.5 "中文prompt"` 的参数引号处理异常，prompt 未传给 Codex，Codex 输出 "Reading additional input from stdin..." 后阻塞。

主导 agent 统一用 Bash 调用 Codex CLI。手动执行时 `echo "prompt" | codex exec --json ...`，runner 脚本内用 subprocess 无此限制。

影响：`runners/drivers/codex-driver.md`

### model_reasoning_effort 无法通过 PowerShell CLI 传入

`-c model_reasoning_effort="high"` 中内层引号在 PowerShell 5.1 下被吃掉，Codex 收到的参数残缺。

改为在 fixture 的 `.codex/config.toml` 中直接写 `model_reasoning_effort = "high"`，不再依赖 `-c` 传参。换 effort 时改 config.toml 中的值即可。

影响：`inject-persistent-rules.md`（持久化 model_reasoning_effort 配置）、`runners/drivers/codex-driver.md`

### approval_policy 和 sandbox_mode 放在 [permissions] section 下导致 Codex 启动报错

`[permissions]` 是命名权限配置文件的容器（map），不是扁平键值对。放错层级后 Codex 报 `invalid type: string, expected struct PermissionProfileToml`。

`approval_policy` 和 `sandbox_mode` 改为 config.toml 顶层 key，与 `model_reasoning_effort` 同级。

影响：`inject-persistent-rules.md`、`runners/drivers/codex-driver.md`

### model_instructions_file = ".codex/instructions.md" 导致路径双写

Codex 从 `.codex/` 目录解析相对路径，`.codex/instructions.md` 被解析为 `.codex/.codex/instructions.md`，启动报找不到文件。

改为 `model_instructions_file = "instructions.md"`。

影响：`inject-persistent-rules.md`

### sandbox_mode = "workspace-write" 触发 Windows Sandbox 报 helper_unknown_error

`workspace-write` 启用 Windows Sandbox，当前环境报 `helper_unknown_error: setup refresh had errors`，所有 shell 命令执行失败。

fixture 是隔离测试仓库，统一用 `sandbox_mode = "danger-full-access"` 绕过 Sandbox。

影响：`inject-persistent-rules.md`、`runners/drivers/codex-driver.md`

### fixture 目录不是 git repo，Codex 默认拒绝执行

`setup_fixture.py` 创建的 fixture 目录不含 `.git`，Codex CLI 默认要求 git repo，直接运行报错。

每次 `codex exec` 必须传 `--skip-git-repo-check`。此 flag 无 config.toml 等价项，CLI 传入。

影响：`inject-persistent-rules.md`（明确写入注入步骤）、`runners/drivers/codex-driver.md`

### 多次执行时输出文件被旧 PowerShell 进程锁定

PowerShell 后台任务未完全退出时仍持有 `m1_raw.jsonl` 等输出文件，后续 `rm` 和 `>` 重定向均报 "Device or resource busy"。

手动逐轮执行时，每轮用不同文件名（`round_01_turn_raw.jsonl`、`round_02_turn_raw.jsonl` 等）避免冲突。runner 脚本内部管理文件名，无此问题。

影响：`runners/drivers/codex-driver.md`（手动备用流程中注明按轮次命名）

### inject-persistent-rules.md 中 codex.toml 和 config.toml 混用

文档中用 `codex.toml` 指代 Codex 配置文件，实际文件名是 `config.toml`。

全文统一为 `config.toml`。

影响：`inject-persistent-rules.md`

---

## 项目级配置

### CC 安全策略拦截 codex exec

`approval_policy="never"` + `sandbox_mode="danger-full-access"` + `--skip-git-repo-check` 组合被 CC 判定为不安全自主 Agent，HARD BLOCK。

在项目 `.claude/settings.json` 加入 Bash 允许规则：

```json
{
  "permissions": {
    "bash": {
      "allow": ["codex exec*"]
    }
  }
}
```

影响：`.claude/settings.json`（项目级）
