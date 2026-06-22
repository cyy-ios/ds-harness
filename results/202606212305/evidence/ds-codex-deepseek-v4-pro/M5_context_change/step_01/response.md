`python -m mini_harness run` 加 `PYTHONPATH` 可从子目录正常工作。现在配置子目录使其开箱可用。
Now verify the path injection works for pytest and write a test exercising `mini_harness` from the subdir:
Let me use `pythonpath` in `pyproject.toml` — the pytest-native way to add paths:
路径计算差了一层。修复 `test_subdir_harness.py` 中 REPO 计算：
同样修复 `conftest.py`：
Subdir 全部通过。验证主线测试也正常：
Let me read the existing implementation and test files to understand the current state.
Now let me run the tests from both the repo root and the workbench subdirectory to see the current state.
All 9 tests pass. Let me also verify the CLI works and inspect the data/config files to confirm correctness.
Now let me read all the key source files and test files to understand the current state.
Now let me read the test files and configs.
Let me check the data files and the acceptance evidence to understand the expected behavior.
I have a clear picture. Let me plan the fixes and apply them.
Starting with `config.py` — adding `sources` as an alias for `inputs` in the parsed config filter.
Let me try a different approach with apply_patch — freeform syntax.
Config fix applied. Now the `subdir/workbench/mini_harness/` shim for cwd-independent `python -m mini_harness`.
`__main__.py` has encoding corruption. Let me rewrite it properly.
Shim is clean. Now steps 3 and 4 together: change `run_dag` to return the report dict, add `memory_summary.md` reference, and update the `_report` function.
Now let me read the test files and the subdir/workbench files to understand the full picture.
Let me run the existing tests to see the current state, and also check config/data files.
I can see the bug. `run_dag` returns the report dict instead of the output path. Let me also check the config files and data to understand everything, then fix it.
Good. I can see the core bug: `run_dag` returns the report dict instead of the output path. Let me also check that `python -m mini_harness run` works from both locations.
The two issues are clear:

1. **`run_dag` returns a dict** instead of the output path — the tests and CLI expect a path.
2. **`python -m mini_harness run` from `subdir/workbench` fails** — the shim package shadows the real one.

Let me fix both.