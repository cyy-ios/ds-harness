也跑一下主仓库的测试确保跨目录完整：
从 `subdir/workbench` 一切正常：

- `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` 可执行，内部路径基于 `REPO_ROOT` 解析，不依赖 CWD
- 主仓库 12 条测试、子目录 1 条本地测试全部通过

中间层的 `config.py` 里 `_resolve_repo_root()` 从自身文件位置向上查找 `pyproject.toml`，保证无论从哪个目录调用，`REPO_ROOT` 稳定指向仓库根。路径解析 (`_resolve_repo_path`) 对相对路径一律以 `REPO_ROOT` 为基准，所以切换工作目录不影响数据文件定位和输出落盘。