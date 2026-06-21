我已经读过 `skills/data-harness/SKILL.md` 并跑过全量 pytest，现有 7 个测试通过；接下来针对“调试输出较多”的问题收敛 CLI 输出，同时保留写入报告文件的完整明细。
定位到 CLI 现在把完整报告直接打到 stdout，包含 records/rejects/logs；在数据或调试日志较多时，这会让验证输出非常膨胀。我要把 stdout 改成稳定摘要，完整报告仍写入 `--output` 指定文件。
实现已收敛到 CLI 边界：runner 的报告仍是事实来源，CLI 只投影一个小摘要。接着补一个回归测试，确保 stdout 不再携带明细日志，但报告文件仍保留完整结果。
变更已经加上回归覆盖。现在用仓库内命令跑测试和一次 CLI 验证，都会禁用字节码写入以避免 `pycache` 污染。
验证通过，CLI 现在只输出摘要，完整 `logs/records/rejects` 留在报告文件里。最后我会清掉这轮验证生成的临时目录和 pytest 缓存，然后确认工作区改动范围。
报告文件检查也符合预期：stdout 是摘要，文件内有真实明细。`memory/memory_summary.md` 存在但内容显示为乱码，我会在最终只保守说明已查看该文件，不把乱码内容当作事实依据。
已修复：`mini_harness run` 现在 stdout 只输出简洁摘要，避免在调试/日志较多时把完整 `records/rejects/logs` 打爆；完整真实报告仍写入 `--output` 文件，并新增 `output` 字段方便追踪。

已补回归测试覆盖“stdout 简洁、报告文件保留明细”。验证通过：

```text
python -B -m pytest -q
8 passed in 0.50s

python -B -m mini_harness run data/input.csv data/events.jsonl --output tmp/acceptance-report.json
{"output": "tmp/acceptance-report.json", "processed_count": 4, "rejected_count": 2, "retry_count": 0, "source_files": ["data/input.csv", "data/events.jsonl"]}
```

已清理本轮生成的 `tmp/` 和 `.pytest_cache/`。也已查看 `memory/memory_summary.md`，但该文件内容显示为乱码，所以未把其中内容作为事实依据。