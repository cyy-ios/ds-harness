# Codex Unoptimized + DeepSeek V4 Deductions

- Corrected acceptance: `M8_compact_resume/step_01/acceptance.json` now has `final_gate_passed=true` and all six checks pass.
- Remaining deductions are qualitative: M5 cwd handling had several false starts, and M8 synchronized root-package work into `src/mini_harness` late.
- Optional `stage_overrides` is not part of the public fixture contract, so its hidden retry test is skipped rather than counted as a final-gate failure.
- `commands.log` is empty for this Codex evidence shape; scoring used `replay.jsonl`, `response.md`, `diff.patch`, and acceptance evidence.
