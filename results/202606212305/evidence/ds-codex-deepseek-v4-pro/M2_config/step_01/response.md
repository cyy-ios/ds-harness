Now update CLI and runner to integrate config:
Now create test configs and verify:
Now full integration tests:
所有实现已就绪，逐项核验如下：

- `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` → 产出 `tmp/report.json`（processed_count=4, rejected_count=2, retry_count=0）
- `python -m mini_harness run --config config.json` → 使用 JSON 配置，写入 `tmp/report_json.json`
- `python -m mini_harness run --config config.yaml` → 使用内置最小 YAML 解析器，写入 `tmp/report_yaml.json`
- `python -m mini_harness run`（无参数）→ 自动探测 repo root 的 `config.yaml`，配置缺省生效
- `python -m mini_harness`（无子命令）→ 打印 help 后 exit 1
- `from mini_harness.runner import run_dag, HarnessError` 导入正常

现有文件结构：`mini_harness/__init__.py`、`__main__.py`、`cli.py`、`config.py`、`runner.py`。`config.py` 内嵌最小 YAML 解析器，支持 JSON/YAML 两种格式，覆盖缺省配置和 `--config` 显式路径，无第三方依赖。`runner.py` 串联 extract → clean → report DAG，失败重试最多 2 次，日志包含 attempt/stage/status。report 包含 SKILL.md 要求的全部字段。