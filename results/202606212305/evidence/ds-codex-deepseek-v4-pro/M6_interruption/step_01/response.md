`logs/unrelated_error.log` — 外部缓存超时日志，与 mini_harness 无关：请求17超时后重试成功，恢复。

`docs/handoff-note.md` — 上一位执行者交的草稿，声称 pytest 全量通过。实测已过时：`run_dag` 返回 dict 而非路径，两个测试因此失败。

回到主线，我先确认文件当前状态，然后修复两个 bug。
Bug 清晰了：`run_dag` 返回 dict 而非路径；subdir shim 包遮蔽了真实 `mini_harness`。修复。