已新增 `src/mini_harness/report.py` 并把实现迁到 `src/mini_harness`，保留 `python -m mini_harness` shim；报告字段、M4 noisy CSV、M7 memory 引用都已覆盖。

验证通过：`python -m pytest -q` 为 `9 passed`，CLI 生成 `tmp/acceptance-report.json` 结果为 `4/2/0`。