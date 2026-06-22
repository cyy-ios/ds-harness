Now let me write a real test file and run it to surface the actual issues.
Now let me run the tests first to confirm the current state:
4 passed, 1 failed — exactly as described. The fix is in `find_config`: explicit path missing should return `None` (fall back to defaults) instead of raising.
Now run the tests:
All 5 pass. Now verify the core CLI command still works:
全部通过：6/6 测试（含 `test_placeholder.py`），`python -m mini_harness run` 两种场景均正常运行。

修复内容：`mini_harness/config.py` 中 `find_config()` 的显式路径不存在行为，从抛 `ConfigError` 改为返回 `None`，使 `load_config` 此时回退到 `DEFAULT_CONFIG`。