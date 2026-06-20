# 当前进度

更新日期：2026-06-08

## 当前状态

- 已选择 Codex 作为 DeepSeek harness 底座。
- `codex/` 保持上游 `main` 基线；`ds-codex/` 为 `deepseek-harness` 开发 worktree。
- 已移除候选仓库源码，参考 commit 见 `docs/reference/harness-comparison.md`。
- 已安装 Rust 1.95、Visual C++ Build Tools 和 Windows SDK。
- Codex `codex-api` 基线测试：108/108 通过。
- 本机运行 localhost 测试需设置 `NO_PROXY=127.0.0.1,localhost`。

## 下一步

1. 定位 Codex provider、Responses 请求、SSE 解析和模型能力映射的最小改造边界。
2. 在 `ds-codex/` 增加 DeepSeek 原生 provider，使其不依赖外部代理调用 DeepSeek。
3. 跑通文本响应、流式响应、工具调用和错误转换。
4. 用 `codex exec --json` 建立 Codex+DeepSeek 任务效果基线。

## 记录规则

- 成功测试只记录名称、数量、日期和关键环境，不保存完整日志。
- 仅保存失败证据、难复现问题和关键基准原始结果到 `internal/runs/<run-id>/`。
