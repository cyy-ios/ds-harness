从 `subdir/workbench` 验证主线功能可用：位置参数 CLI 正常产出 `processed_count=4/rejected_count=2/retry_count=0`，并且 `$env:PYTHONPATH=...\src; python -m pytest ..\..\tests -q -p no:cacheprovider` 通过，`9 passed in 0.28s`。

已清理本次 `tmp/workbench-*` 输出；未发现 `__pycache__`。