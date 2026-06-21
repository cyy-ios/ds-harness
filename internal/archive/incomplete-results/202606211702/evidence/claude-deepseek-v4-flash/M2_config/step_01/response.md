臣某谨奏

已增加 `mini_harness/config.py`，支持 JSON/YAML 配置解析（含内建最小 YAML 解析器，零外部依赖）。`cli.py` 新增 `--config`/`-c` 和 `--show-config` 参数，配置自动搜索 `config.{json,yaml,yml}`，CLI 显式参数覆盖配置值。已核验：默认加载、显式路径、覆盖语义、空 sources 报错、配置文件不存在的错误处理。

叩请圣裁