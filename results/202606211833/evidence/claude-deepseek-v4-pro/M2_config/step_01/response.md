臣某谨奏

已增加 JSON/YAML 配置解析，保留 `run` 子命令，支持配置缺省（自动扫描 CWD 下的 `mini_harness-config.{json,yaml,yml}`）和 `--config`/`-c` 显式路径。CLI 参数优先于配置文件。

新增 `mini_harness/config.py`，更新 `mini_harness/cli.py`。

验证通过：
- `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` ✓
- `python -m mini_harness run --config tmp/acceptance-config.json` ✓
- `python -m mini_harness run --config mini_harness-config.yaml` ✓
- 无配置文件且无 CLI 参数时提示错误 ✓
- CLI 参数覆盖配置文件值 ✓
- `python -m pytest tests/` 1 passed ✓

叩请圣裁