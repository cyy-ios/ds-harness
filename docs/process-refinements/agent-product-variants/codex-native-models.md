# Codex CLI + 原生模型跑通记录

日期：2026-06-19  
变体：Codex CLI + Codex 原生模型（如 GPT-5.5）  
用途：记录第一次把 Agent Eval Suite 跑到 Codex 原生模型时遇到的问题和修正。

## 背景

最初评测对象主要是 DeepSeek 裸模型和 DeepSeek 接入 Codex 后的变体。为了建立 Agent 产品基线，需要让官方 Codex CLI 直接连接自己的原生模型，并跑同一套 M1-M8 fixture。

## 问题与修正

### 1. 模型注册缺少 GPT 系列

`models.yaml` 早期只登记 DeepSeek 相关模型，主流程无法把用户指定的 GPT 模型映射到 Codex CLI 的 `-m` 参数。

修正：为原生模型增加显式 key，并记录 reasoning effort 等模型参数。后续新增模型按同样格式登记。

### 2. PowerShell 传中文 prompt 容易卡在 stdin

在 PowerShell 5.1 下直接执行 `codex exec --json -m <model> "中文 prompt"` 时，prompt 可能没有正确传给 Codex，Codex 进入 “Reading additional input from stdin...” 状态。

修正：runner 使用 `subprocess.run(input=prompt)` 传入 prompt；手工调试时用管道输入，避免复杂 shell quoting。

### 3. `model_reasoning_effort` 不适合依赖临时 CLI 参数

`-c model_reasoning_effort="high"` 在某些 shell 下引号会被错误处理，导致 Codex 收到残缺配置。

修正：把稳定参数写入 fixture 的 `.codex/config.toml`，只把必要的动态参数留给 CLI。

### 4. Codex config 层级容易写错

`approval_policy` 和 `sandbox_mode` 是顶层 key，不属于 `[permissions]`。放错层级会触发 Codex 配置解析错误。

修正：统一使用顶层配置，并在注入文档里写明文件名是 `config.toml`，不是 `codex.toml`。

### 5. `model_instructions_file` 相对路径规则容易误解

Codex 从 `.codex/` 目录解析相对路径。写成 `.codex/instructions.md` 会变成 `.codex/.codex/instructions.md`。

修正：写成 `instructions.md`。

### 6. Windows sandbox 在本机环境不稳定

`sandbox_mode = "workspace-write"` 触发 Windows Sandbox helper 错误，导致 shell 命令失败。

修正：fixture 是隔离临时仓库，评测时统一使用 `danger-full-access`，用 fixture 边界和结果校验控制风险。

### 7. fixture 不是 git repo，Codex 默认拒绝执行

Codex CLI 默认要求在 git repo 中运行；fixture 是临时目录，未必初始化 git。

修正：runner 固定传 `--skip-git-repo-check`。

### 8. 输出文件被 PowerShell 后台进程锁定

手工多轮调试时复用同一个 raw JSONL 文件，可能被旧进程占用。

修正：按轮次命名 raw 输出；正式 runner 内部管理文件名。

## 当前状态

主流程已把 Codex 原生模型作为第 4 条运行路径：

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py   --root ${fixture_root}   --out ${result_root}/evidence/codex-native   --variant native   --model gpt-5.5
```
