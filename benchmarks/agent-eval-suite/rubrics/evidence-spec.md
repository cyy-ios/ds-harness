# Evidence 目录规范

Evidence 是评分输入，不是报告输出。

裸模型 runner：

```text
evidence/<variant>/
  index.yaml
  fixture_files/
  round_01/
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

Codex runner：

```text
evidence/<variant>/
  run_summary.json
  fixture_files/
  M1_bootstrap/step_01/
    prompt.json
    response.md
    replay.jsonl
    diff.patch
    source_snapshot/
    artifact/
    acceptance.json
    analyzer_output/
    cost.json
```

评分 agent 必须兼容两种结构。
