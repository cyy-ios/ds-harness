已读取 `skills/data-harness/SKILL.md`，接下来只改包内配置解析和对应测试。
已完成：新增 JSON/YAML 配置解析，保留 `mini_harness run` 子命令，并支持默认 `harness.json/yaml/yml` 与 `--config` 显式路径；路径仍按 repo root 解析，符合 `memory/memory_summary.md` 的早期决策。

已核验：`PYTHONDONTWRITEBYTECODE=1 python -m pytest -q` 通过，结果 `6 passed`；已清理 `.pytest_cache`，未发现 `__pycache__`。