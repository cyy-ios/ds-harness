已完成：保留 `run` 子命令，新增 JSON/YAML 配置解析，支持默认查找 `mini_harness.json|yaml|yml` 和 `--config` 显式路径；CLI 参数仍可覆盖配置里的 `sources/output`，缺省输出为 `tmp/report.json`。

已核验：
`python -B -m pytest -q` 通过，`6 passed`。
`python -B -m mini_harness run --config tmp/json-config.json` 通过。