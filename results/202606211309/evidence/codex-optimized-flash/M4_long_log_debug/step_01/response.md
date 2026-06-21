Let me look more carefully at the full repo state — maybe there were test files that got cleaned up, or other artifacts.
找到问题：写入文件的报告缺少 `report/ok` 日志条目。原因是 `_log(attempt, "report", "ok")` 在 `_write_report` 之后执行，导致日志捕获不完整。
Now let me write proper tests and replace the placeholder.
Let me check the current test state and understand what's failing:
Now I can see the two issues clearly:

1. **`test_run_subcommand_help`**: argparse raises `SystemExit` on `--help`, which the test doesn't handle correctly
2. **`_to_snake_case("HTTPResponse")`**: The acronym lookahead extends too far, treating `R` as part of the `HTTP` acronym instead of the start of `Response`

Let me fix both:
Now let me verify all tests pass:
All 16 tests pass. Let me also validate the CLI entry points:
全部 16 个测试通过，CLI 入口可用。以下是修复总结：

**修复的两个问题**

1. **`test_snake_case_maps_acronyms`** — `_to_snake_case("HTTPResponse")` 返回 `"httpresponse"` 而非 `"http_response"`  
   - 根因：首字母缩略词向前扫描时将尾部大写字母（`R`）一并归入缩略词，导致 `"httpr"` + `"esponse"`。  
   - 修复：在 `mini_harness/runner.py` 的 `_to_snake_case` 中，当连续大写块后紧跟小写字母时，将最后一个大写字母留给下一个词（`HTTP` + `Response` → `http_response`）。

2. **`test_run_subcommand_help`** — `argparse` 在 `--help` 时抛出 `SystemExit(0)` 异常，测试未捕获。  
   - 修复：测试改用 `try/except SystemExit` 包装调用，允许正常退出码 0 或异常两种路径。

**修改文件**

- `mini_harness/runner.py` — 修复 acronym 边界判定
- `tests/test_mini_harness.py` — 修复 SystemExit 处理