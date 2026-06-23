已增加 JSON/YAML 配置解析：`run` 子命令保留，支持默认 `harness.json|harness.yaml|harness.yml`，也支持 `--config` 显式路径，CLI 参数可覆盖配置里的 `output`。

已核验：`python -m pytest -q -p no:cacheprovider` 通过 `6 passed`；旧命令 `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 仍可用。