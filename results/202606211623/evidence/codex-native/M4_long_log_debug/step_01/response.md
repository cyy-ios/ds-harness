定位到 `data/m4_noise_test.csv` 的注释/噪声行被 `csv.DictReader` 当成表头和记录，导致真实数据全被 reject。
我会把这个噪声 CSV 场景固化成单测，防止以后回退。
已补实现和回归测试；现在跑 unittest、pytest 以及噪声输入的 CLI 验证。
已修复：CSV 读取现在跳过空行和 `#` 开头的调试/噪声行，`data/m4_noise_test.csv` 会得到真实结果 `processed_count=2`、`rejected_count=1`，并新增回归测试覆盖该场景。

已验证：`python -m unittest discover -s tests` 7 个通过、`python -m pytest -q` 8 个通过、`python -m mini_harness run data/m4_noise_test.csv --output tmp/m4-report.json` 结果正确，且未产生 `__pycache__`；复盘引用：`memory/memory_summary.md`。