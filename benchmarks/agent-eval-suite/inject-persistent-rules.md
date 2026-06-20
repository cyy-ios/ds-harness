# 注入预设规则

被测 agent 如果是 Codex/CC 产品形态，必须在启动被测 agent 会话之前注入持久规则。裸模型（API）跳过本步骤——`run_deepseek_agent_replay.py --rules` 已处理。

## 判断是否执行

| 被测形态 | 执行本步骤 |
|----------|-----------|
| bare-model（API 调 DeepSeek） | 跳过 |
| harness-codex（Codex CLI） | 执行 |
| CC（Claude Code CLI） | 执行 |

## 规则内容

原文在 `persistent-rules.example.md`。注入时逐字复制该文件全部内容，**禁止改写、删减或添加**（包括换行、缩进、标点）。

## 注入时机

fixture 搭完后（`setup_fixture.py` 已跑完）、首次启动被测 agent 之前。

## 还原时机

所有 M1-M8 执行完 + 评分完 + 报告出完之后。

---

## Codex（harness-codex）

### 注入

在 `${fixture_root}/` 下执行：

**1. 写 instructions 文件**

```
Write: ${fixture_root}/.codex/instructions.md
内容: persistent-rules.example.md 的完整内容（逐字复制）
```

**2. 备份 config.toml（如果存在）**

```
如果 ${fixture_root}/.codex/config.toml 存在:
  cp ${fixture_root}/.codex/config.toml ${fixture_root}/.codex/config.toml.bak
```

**3. 确保 model_instructions_file 和 model_auto_compact_token_limit 配置生效**

检查 `${fixture_root}/.codex/config.toml` 是否已有 `model_instructions_file`。如果没有则追加：

```toml
model_instructions_file = "instructions.md"
model_auto_compact_token_limit = 38000
```

如果已有 `model_instructions_file` 但路径不同，改为上述值，原值记在注释中。
如果已有 `model_auto_compact_token_limit` 但值不同，改为 38000，原值记在注释中。

> 38000 确保 M1-M7 累计 ~25-45k token 后，compact 在 M7 末尾或 M8 开头触发。

**4. 确保 approval_policy 和 sandbox_mode 配置生效（跳过权限确认）**

检查 `${fixture_root}/.codex/config.toml` 是否已有 `approval_policy` 和 `sandbox_mode`（顶层 key）。如果没有则追加：

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
```

如果已有但值不同，改为上述值，原值记在注释中。

**5. 每次 `codex exec` 调用额外传入 `--skip-git-repo-check`**（无 config.toml 对应项，必须 CLI 传）。

### 还原

```bash
# 删除注入文件
rm ${fixture_root}/.codex/instructions.md

# 恢复 config.toml
如果 config.toml.bak 存在:
  mv ${fixture_root}/.codex/config.toml.bak ${fixture_root}/.codex/config.toml
否则:
  从 ${fixture_root}/.codex/config.toml 中删除注入时新增的行（model_instructions_file、model_auto_compact_token_limit、approval_policy、sandbox_mode）
```

---

## CC（Claude Code CLI）

### 注入

CC 自动从当前工作目录及父目录加载 `.claude/CLAUDE.md`，因此在 fixture root 下准备该文件：

**1. 备份已有的 CLAUDE.md（如果存在）**

```
如果 ${fixture_root}/.claude/CLAUDE.md 存在:
  cp ${fixture_root}/.claude/CLAUDE.md ${fixture_root}/.claude/CLAUDE.md.bak
```

**2. 写持久规则**

```
Write: ${fixture_root}/.claude/CLAUDE.md
内容: persistent-rules.example.md 的完整内容（逐字复制）
```

如果已有 CLAUDE.md，把持久规则内容**追加**到已有文件末尾（用空行分隔），不要覆盖原有内容。

### 还原

```bash
# 如果原本有 CLAUDE.md.bak:
mv ${fixture_root}/.claude/CLAUDE.md.bak ${fixture_root}/.claude/CLAUDE.md

# 如果原本没有 CLAUDE.md（即本次新建的）:
rm ${fixture_root}/.claude/CLAUDE.md
```

---

## 兜底

无论主导 agent 在评分阶段是否报错退出，还原步骤必须在最后执行。如果主导 agent 中途崩溃，手动运行还原命令。
