臣某谨奏

已增加 `mini_harness/config.py`，支持 JSON/YAML 配置解析（YAML 优先用 PyYAML，不可用时走内置最小实现）。CLI 新增 `--config/-c` 选项，`sources` 改为可选（可从配置读取），`--output` 和 `--max-retries` 支持 CLI 覆盖配置。原 `run` 子命令结构完整保留。

核验：JSON 配置、YAML 配置、CLI 覆盖、缺省报错均已通过。

叩请圣裁