# 全量证据包

每步由 harness 脚本自动采集的固定文件清单。采集和判分解耦。

| 文件 | 内容 | 采集方式 |
|------|------|---------|
| `prompt.json` | 该步的完整 prompt | harness 自动 |
| `response.md` | agent 的完整回复 | harness 自动 |
| `replay.jsonl` | 完整 tool call 序列 | harness 自动 |
| `commands.log` | 命令、cwd、退出码、stdout/stderr | harness 自动 |
| `diff.patch` | 该步前后的文件变更 | harness 自动 |
| `file_tree.txt` | 该步结束时的文件树 | harness 自动 |
| `source_snapshot/` | 该步结束时的源码/配置/测试 | harness 自动 |
| `artifact/` | CLI 输出、报告 JSON 等产物 | harness 自动 |
| `acceptance.json` | 验收脚本输出 | 脚本运行 |
| `cost.json` | token、耗时、命令次数 | harness 自动 |
