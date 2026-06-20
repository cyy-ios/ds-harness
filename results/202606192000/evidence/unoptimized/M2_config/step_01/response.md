现状清楚：`config.py` 已有 JSON/YAML 解析，但 `cli.py` 的 `run` 子命令尚未接入配置系统。需要把配置缺省发现和显式 `--config` 路径接入 CLI。
核验：跑现有测试 + CLI `run --help` + 实际输入文件。
测试全过。CLI 模块路径问题：`python -m mini_harness` 需要 `src` 在 path 上。
CLI `run --help` 正常。现在跑实际流水线：无配置 + 显式配置。
PowerShell heredoc 加了 BOM。修两处：删 BOM 重建文件，同时让 `_load_json` 容错 BOM。
自动发现配置生效。再测显式 `--config` + YAML 配置 + `--max-retries` 覆盖。
全通。核验产物和日志。
报告含 `processed_count=2, rejected_count=1`，日志含 `attempt/stage/status` 三字段。清理临时文件并做最终核验。
YAML 解析有 bug：根级多键映射只返回了第一对。修 `_parse_yaml` 直接委托 `_parse_yaml_dict`。
多键 YAML 解析正确。最终全量核验。
臣某谨奏

改动完成。三文件变更：

- **`cli.py`**：`run` 子命令新增 `--config`（显式路径）和 `--max-retries`（覆盖配置）；无 `--config` 时自动调用 `find_default_config` 发现仓库根目录下的 `mini_harness.json/yaml` 或 `config.json/yaml`。
- **`pipeline.py`**：`run_pipeline` 接受 `max_retries` 参数，缺省为 2；配置中的 `max_retries` 作为默认值，CLI `--max-retries` 可覆盖。
- **`config.py`**：修复 `_parse_yaml` 多键根映射只返回首对的 bug（改为直接委托 `_parse_yaml_dict`）；`_load_json`/`_load_yaml` 使用 `utf-8-sig` 容错 BOM。

核验结果：`pytest tests/` 7/7 通过；`python -m mini_harness run --input data/input.csv` 和 `--input data/events.jsonl` 均正常产出报告。

叩请圣裁