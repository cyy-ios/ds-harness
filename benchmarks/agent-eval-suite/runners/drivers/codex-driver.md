# Codex Agent 产品 Driver

用 CC 主导，通过 Bash 调 Codex CLI，以同 session 连续方式跑 M1-M8。

## 变体

| 变体 | 含义 | 模型 |
|------|------|------|
| `native` | 官方 Codex CLI 直连 Codex 原生模型 | GPT-5.5、GPT-5.4 等 |
| `unoptimized` | 官方 Codex CLI + Python proxy 翻译 | DeepSeek（通过代理） |
| `optimized` | ds-codex Rust fork 内建 DeepSeekChat 适配 | DeepSeek（直连） |

`unoptimized` 变体由 runner 自动管理 8898 代理生命周期，`native` 和 `optimized` 直连无需代理。

## 前置

- Codex CLI 已安装（`codex` 在 PATH）
- `optimized` 变体需 ds-codex 二进制已编译（`ds-codex/codex-rs/target/debug/codex.exe`）
- `DEEPSEEK_API_KEY` 已设置（`<local-deepseek-api-key-file>`）

## 流程

### 1. 搭 fixture

```bash
python3 runners/setup_fixture.py ${fixture_root}
```

### 2. 注入持久规则

按 `inject-persistent-rules.md` 执行。注入后 fixture 的 `.codex/config.toml` 含顶层 `approval_policy = "never"` 和 `sandbox_mode = "danger-full-access"`，确保非交互执行。

### 3. 触发测试

```bash
# native 变体（Codex 原生模型）
python3 runners/run_codex_replay.py --root ${fixture_root} --variant native --model gpt-5.5

# unoptimized 变体（DeepSeek 代理）
python3 runners/run_codex_replay.py --root ${fixture_root} --variant unoptimized

# optimized 变体（ds-codex 直连 DeepSeek）
python3 runners/run_codex_replay.py --root ${fixture_root} --variant optimized
```

证据落在 `${fixture_root}/evidence/`。

### 4. 评分

同裸模型流程，按 `rubrics/` 评分。

### 5. 还原持久规则

按 `inject-persistent-rules.md` 还原。

## 手动逐轮执行（备用）

runner 不可用时，可手动逐轮调 codex exec：

### 首轮

```bash
codex exec --json --skip-git-repo-check -m <model_slug> "里程碑 M1_bootstrap：<prompt>"
```

记录输出的 `session id`（从 JSONL 中提取 `thread_id`）。

### 后续轮（M2-M8）

```bash
codex exec --json --skip-git-repo-check resume <session_id> "里程碑 M2_config：<prompt>"
codex exec --json --skip-git-repo-check resume <session_id> "里程碑 M3_runner_retry：<prompt>"
...
```

每轮输出存入 `round_N/turn_raw.jsonl`，然后：

```bash
python3 runners/codex2replay.py round_N/turn_raw.jsonl ${fixture_root} evidence/round_N/ <milestone_id> "<prompt>"
```

## 模型指定

| 场景 | 参数 |
|------|------|
| GPT-5.5 high | `-m gpt-5.5 -c model_reasoning_effort="high"` |
| GPT-5.5 medium | `-m gpt-5.5 -c model_reasoning_effort="medium"` |
| GPT-5.1 Codex Max | `-m gpt-5.1-codex-max` |
| 自定义模型 | `-c model_catalog_json="<path>" -m <slug>` |

`-c` 参数也可以在 fixture 的 `.codex/config.toml` 中持久化，避免每次传。

## 验证记录

2026-06-19：`codex exec -m gpt-5.5` 首轮 → `codex exec resume <thread_id>` 续轮，跨轮上下文保持验证通过。首轮创建 a.txt(hello)，续轮能读取 a.txt 并基于其内容创建 b.txt(world)。

2026-06-19：两变体从 CC 触发验证通过。`unoptimized` → proxy(8898) → DeepSeek 返回正常；`optimized` → ds-codex 直连 DeepSeek 返回正常。
