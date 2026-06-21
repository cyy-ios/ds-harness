臣某谨奏

定位：`cli.py` 模块级的 `logging.basicConfig` 在导入时即配置根 logger，pytest 等测试框架无法捕获日志输出，且日志句柄泄漏到测试环境。

修复：将 `basicConfig` 移入 `main()` 函数内部，仅在 CLI 实际运行时配置；用 `force=True` 确保重复调用也能生效。导入时不再产生日志句柄（`root logger handlers: []`）。

所有验收场景核验通过：CLI 参数运行、`--config` 显式配置运行、`--show-config`、无配置报错。

叩请圣裁