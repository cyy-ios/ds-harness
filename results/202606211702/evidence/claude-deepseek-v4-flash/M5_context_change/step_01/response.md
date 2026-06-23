臣某谨奏

在 `utils.py` 增加 `repo_root()`（`git rev-parse --show-toplevel`），`cli.py` 和 `config.py` 中所有相对路径均据此解析为 repo-root 绝对路径。从 `subdir/workbench` 和 repo root 双方向核验通过，`processed=4 rejected=2` 结果一致。

叩请圣裁