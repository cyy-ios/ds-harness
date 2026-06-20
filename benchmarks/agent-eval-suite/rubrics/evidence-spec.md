# 证据目录结构

评分 agent 以 `evidence/` 为工作根目录，先读 `index.yaml` 了解全局，再遍历各 `round_N/`。

## 目录结构

```
evidence/
  index.yaml              # 轮次索引（round → milestone → prompt）
  fixture_files/           # 关键 fixture 文件副本（skills/ docs/ memory/ benchmarks/）
  round_01/
    prompt.json            # 本轮 prompt
    response.md            # agent 最终回复
    replay.jsonl           # 本轮全部 tool call 事件（多 step 已累积为单文件）
    commands.log           # 本轮全部 shell 命令及输出（JSON 数组）
    diff.patch             # 本轮全部代码变更
    source_snapshot/       # 本轮结束时 src/ tests/ skills/ 快照
    artifact/              # 本轮产物文件（*.json *.md *.txt *.log）
    acceptance.json        # 公开验收脚本输出
    analyzer_output/
      analyzer.json        # analyze_replay.py 结构化信号
    cost.json              # 本轮 token 数 / 耗时 / tool step 数
  round_02/
    ...
  round_N/
```

## 文件说明

- **index.yaml**：先读此文件，含 `subject`（被测对象）、`task`（任务名）、`timestamp`（采集时间戳，格式 `YYYYMMDDHHmm`）、`total_rounds`、`rounds`（每轮的 round / milestone / prompt）。由 `collect_evidence.py` 在采集结束时自动生成。
- **fixture_files/**：持久规则、旧文档、memory、handoff、compat/perf 等 fixture。证据引用中 `fixture_files/xxx` 即指此目录。
- **prompt.json**：含 `round` 字段（如 `round_01`）和 `prompt` 字段（本轮给 agent 的输入文本）。
- **response.md**：agent 本轮最终回复文本。
- **replay.jsonl**：每行一条 JSON，role 为 `assistant`（含 tool_call）或 `tool`（含 result）。一轮内所有 tool step 的事件已按顺序累积在同一个文件中。
- **commands.log**：JSON 数组，每项含 command / cwd / exit_code / stdout。仅收集 shell 类 tool call。
- **diff.patch**：本轮全部代码变更（相对本轮开始时的 git snapshot）。
- **source_snapshot/**：本轮结束时 `src/` `tests/` `skills/` 三个目录的完整副本。
- **artifact/**：本轮在工作区根目录下产出的 JSON/MD/TXT/LOG 文件及 `tmp/` 目录内容的副本。
- **acceptance.json**：`score_mini_data_harness.py` 的公开验收输出。
- **analyzer_output/analyzer.json**：`analyze_replay.py` 的结构化信号，含 `signals`（skill_read / pytest_run / memory_read 等布尔值）和 `truthfulness_evidence`（各 M 的真实性风险检查结果）。评分 agent 优先使用此文件的结构化信号，必要时回查原始 replay。
- **cost.json**：本轮的耗时、输入/输出 token 数、tool step 数。
