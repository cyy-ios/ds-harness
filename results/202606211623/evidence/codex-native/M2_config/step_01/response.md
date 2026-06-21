将新增标准库 JSON/YAML 配置加载，`run` 子命令保留；CLI 参数优先于配置，默认配置缺失时不报错，显式 `--config` 缺失时报错。
基础命令已通过；我补一个默认配置覆盖用例，并把测试产生的临时配置/报告纳入清理。
默认配置用例和清理逻辑已补齐；现在重新核验测试、原始 CLI 调用和缓存污染。
核验通过，原有 `run` 调用仍可用；我最后检查工作树和 `tmp` 里残留的新增测试产物。
已增加 JSON/YAML 配置支持：新增 [mini_harness/config.py](/C:/项目/ds-harness/tmp/agent-eval-fixture-202606211623/mini_harness/config.py)，`run` 子命令保留，支持 `--config` 显式路径，也会默认查找 `harness.json`、`harness.yaml`、`harness.yml`；CLI 参数优先于配置。

已核验：`PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests` 通过，原命令 `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 通过，未发现 `__pycache__`。