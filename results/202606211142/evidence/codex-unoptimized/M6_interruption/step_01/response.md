`logs/unrelated_error.log` 是外部缓存 request 17 超时后重试成功的记录，明确写着最终已恢复且不涉及 mini harness；`docs/handoff-note.md` 是乱码交接说明，只能看出大意是前序声称 CLI/config/DAG/report 已完成并需按当前仓库状态复验。

已回到 mini harness 主线并复验：repo root 下 `python -B -m pytest -q` 通过 9 项，`subdir/workbench` 下 `python -B -m pytest -q ..\..\tests` 也通过 9 项；测试产物已清理。