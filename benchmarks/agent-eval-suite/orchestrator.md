# Agent Eval Suite 主流程

这是 Agent / 模型评测的唯一主流程入口。所有命令从仓库根目录执行。公开结果只写入 `results/<YYYYMMDDHHmm>/`。

## 0. 约定

```bash
timestamp=$(date +%Y%m%d%H%M)
fixture_root=tmp/agent-eval-fixture-${timestamp}
result_root=results/${timestamp}
```

目录契约：

```text
results/<timestamp>/
  evidence/<variant>/
  scores/
  scorecard.md
  deductions.md
```

多变体对比可在同一个 `result_root` 下放多个 `evidence/<variant>/`，并把评分写到 `scores/<variant>/`；根目录仍保留汇总 `scorecard.md` 和 `deductions.md`。

## 1. 生成 fixture

```bash
python benchmarks/agent-eval-suite/runners/setup_fixture.py ${fixture_root}
```

fixture 的任务设计见 `benchmarks/agent-eval-suite/tasks/mini-data-harness/scenario.md`。runner 会把同一 session 的 M1-M8 prompt 依次发给被测对象。

## 2. 选择一种运行方式

### 2.1 裸模型：DeepSeek API

用于测试“模型本身 + 简单工具循环”，不经过 Codex 产品层。

```bash
python benchmarks/agent-eval-suite/runners/run_deepseek_agent_replay.py   --root ${fixture_root}   --model deepseek-v4-pro   --out ${result_root}/transcripts/deepseek-v4-pro.jsonl   --evidence-dir ${result_root}/evidence/deepseek-v4-pro
```

密钥来源：优先环境变量 `DEEPSEEK_API_KEY`，也可传 `--key-file <path>`。

### 2.2 Codex 未适配：官方 Codex CLI + DeepSeek proxy

用于测试官方 Codex CLI 通过 OpenAI Responses 兼容代理转接 DeepSeek 的效果。

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py   --root ${fixture_root}   --out ${result_root}/evidence/codex-unoptimized   --variant unoptimized
```

密钥来源：`DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY_FILE`。runner 会自动启动本地 proxy。

### 2.3 Codex 已适配：ds-codex 内建 DeepSeek provider

用于测试改造后的 Codex 直连 DeepSeek。

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py   --root ${fixture_root}   --out ${result_root}/evidence/codex-optimized   --variant optimized
```

前置：`ds-codex/codex-rs/target/debug/codex.exe` 已构建；密钥来源同上。

### 2.4 Codex 原生：官方 Codex CLI + 原生模型

用于测试 Codex 自己接原生模型，作为产品基线。

```bash
python benchmarks/agent-eval-suite/runners/run_codex_replay.py   --root ${fixture_root}   --out ${result_root}/evidence/codex-native   --variant native   --model gpt-5.5
```

前置：Codex CLI 已登录或已配置所需 OpenAI / Codex 凭据。

## 3. Evidence 产物

每个 runner 负责生成 evidence：

```text
evidence/<variant>/
  index.yaml 或 run_summary.json
  fixture_files/
  round_01/ 或 M1_bootstrap/step_01/
    prompt.json
    response.md
    replay.jsonl
    commands.log
    diff.patch
    source_snapshot/
    artifact/
    acceptance.json
    analyzer_output/
    cost.json
```

裸模型 runner 使用 `collect_evidence.py` 的 `round_01..08` 结构；Codex runner 使用 `M*_*/step_01` 结构。评分时两种结构都必须支持。

## 4. 评分

评分 agent 按 `benchmarks/agent-eval-suite/rubrics/scoring-output.md` 执行。主规则：`acceptance.json` 是证据，不是 8 个能力的分数。

1. 读取对应 `evidence/<variant>/` 的全部轮次。
2. 读取 `rubrics/capability-scoring.md`、`rubrics/项目理解-scoring.md`、`rubrics/capability-weights.yaml`、`rubrics/scoring-calibration.md`。
3. 按 8 个能力独立评分，分别生成 `scores/*.score.json`。
4. `score_mini_data_harness.py` / `acceptance.json` 只能作为 evidence 和 deductions 来源；禁止把 acceptance `score` 复制为能力分或逐轮分。
5. 汇总生成 `scorecard.md` 和 `deductions.md`。
6. 多变体对比时，先写 `scores/<variant>/...`，再写根目录汇总报告。

## 5. 完成校验

```bash
python scripts/verify_results_layout.py
```

通过后才算本次 run 可归档。

## 6. 禁止项

- 禁止写入 `benchmarks/agent-eval-suite/results/`。
- 禁止把密钥、token、个人本地 key 文件提交到仓库。
- 禁止把未完成 run 放在公开 `results/` 下；未完成产物放 `internal/archive/incomplete-results/`。
