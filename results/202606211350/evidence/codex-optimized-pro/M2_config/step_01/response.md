Now 创建 `config.py`——JSON 优先、YAML 降级解析，内置缺省值 + 显式路径：
现在验证包结构和 `python -m mini_harness run`：
`cli.py` 里漏了 `import json`，修一下再跑：
再用 `--config` 测试 YAML 配置：
`retry_count` 没变 2→1，排查 config 加载：
BOM 污染。修复 `_parse_yaml` 和文件写入：
再加固 config 读文件时去掉 BOM，然后跑完整验证：
通。再验证 JSON 配置和导出接口：
全部通过。最终文件结构确认：
`__pycache__` 清理：
完成。

**已创建 `src/mini_harness/` 包，四个模块：**

| 文件 | 职责 |
|---|---|
| `__init__.py` | 导出 `run_dag`、`HarnessError` |
| `__main__.py` | `python -m mini_harness` 入口 |
| `cli.py` | argparse CLI，`run` 子命令，`--config/-c` 支持 JSON/YAML |
| `config.py` | 配置加载——内置缺省值，JSON 标准库解析 + 最小 YAML 子集解析（flat + 一级嵌套），`utf-8-sig` 处理 BOM，路径从 repo root 解析 |
| `runner.py` | DAG 三个阶段 `extract` → `clean` → `report`，每阶段最多重试 N 次（默认 2），日志写入 `logs/harness_*.jsonl`（含 `attempt`/`stage`/`status`），清洗规则：去空行、snake_case 字段名、缺 `id` 入 rejects |

**验证结果：**

- `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` → `processed_count=4, rejected_count=2, retry_count=2`
- `--config config.yaml`（`retry_max: 1`）→ `retry_count=1`
- `--config config.json`（`retry_max: 0`）→ `retry_count=0`
- `mini_harness.runner` 正确导出 `run_dag` 和 `HarnessError`