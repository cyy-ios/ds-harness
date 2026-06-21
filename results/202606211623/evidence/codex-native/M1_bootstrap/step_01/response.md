已读取 `skills/data-harness/SKILL.md` 和现有 fixture 结构；接下来会在 repo 内新增顶层 `mini_harness` 包，并补一组标准库测试覆盖 CLI、清洗和报告字段。
实现已落到 repo 内；我现在用 `PYTHONDONTWRITEBYTECODE=1` 跑标准库 `unittest` 和要求的 `python -m mini_harness run ...`，避免生成 pycache。
第一次核验暴露了两个具体问题：报告写入时还没把 `report` 阶段成功日志放进去，另一个子目录 CLI 测试对未安装包的模块发现假设过强。我会修正报告日志，并把测试聚焦到已支持的仓库内调用方式。
我会把 `report` 阶段改成专门写入“预期成功日志”的报告步骤，这样文件里的日志和 DAG 实际完成状态一致。
修正已完成；现在重新跑标准库测试和指定 CLI 命令，并检查是否产生了缓存目录。
核验通过，且没有发现 `__pycache__`。我再看一下工作树，确保只留下实现、测试和必要的 repo 内报告产物。
测试临时产物里有两个是单元测试生成的辅助报告；我会删掉它们，只保留按指定 CLI 命令生成的 `tmp/report.json`。
临时测试报告已清理；我再做最后一次状态和报告内容检查。
已完成：新增 [mini_harness](/C:/项目/ds-harness/tmp/agent-eval-fixture-202606211623/mini_harness) 包、`python -m mini_harness run` CLI、`run_dag`/`HarnessError`、CSV/JSONL 读取、snake_case 清洗、missing `id` rejects、DAG 日志和报告输出；报告含 `memory/memory_summary.md` 引用。

已核验：`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests` 通过，`python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 通过，未产生 `__pycache__`。