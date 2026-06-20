# Agent 产品 CLI 参考

被测 agent 产品的程序化调用方式。主导模型（CC + DeepSeek v4 Pro）通过 Bash 调这些 CLI 驱动测试。

## Codex

- 非交互：`codex exec [OPTIONS] [PROMPT]`
- 交互 TUI：`codex`（同 session 多轮）
- 模型：`-m <slug>`（gpt-5.5, gpt-5.1-codex-max, o3）
- 推理程度：`-c model_reasoning_effort="xhigh"`（low/medium/high/xhigh）
- 配置覆盖：`-c key=value`
- Session 恢复：`codex resume --last`、`codex fork`
- 自定义模型：`-c model_catalog_json="/path/to/custom.json"`
- 本地模型：`--oss` + `--local-provider lmstudio|ollama`

模型注册表：`codex-rs/models-manager/models.json`

## Claude Code

- 非交互：`claude -p "prompt"` / `claude --print`
- 同 session 连续：`claude -p "M1"` → `claude -p "M2" --continue`（`-c`）
- 指定 session：`claude -p "..." --resume <id>`（`-r <id>`）
- 模型：`--model <alias>`（sonnet/opus/haiku/fable/best）或完整 ID
- 推理程度：`--effort low|medium|high|xhigh|max`
- 环境变量：`ANTHROPIC_MODEL`、`CLAUDE_CODE_EFFORT_LEVEL`
- JSON 输出：`--output-format json`（获取 session_id 等）
- 非 Anthropic 模型：设 `ANTHROPIC_BASE_URL` → LiteLLM 网关
  - 网关必须暴露 `/v1/messages`、`/v1/messages/count_tokens`
  - 模型发现：`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`

## 跨产品通用规律

- 模型切换都是一次配置全局生效，不需要每次跑前改
- 非交互模式都有 `--continue`/`--resume` 维持上下文
- session ID 可以从 JSON 输出中获取用于后续恢复
