# DeepSeek V4 Flash Corrected Deductions

Correction: 旧 acceptance 早期轮次误判为 final gate，已按 stage/final_gate_applicable 规则重算.

- Original `acceptance.json` files are preserved and are not overwritten.
- No rerun was performed; corrected scoring uses existing `replay.jsonl`, `commands.log`, `diff.patch`, artifacts, and original acceptance evidence.
- `round_01`-`round_07`: treated as `stage=intermediate`, `final_gate_applicable=false`; their acceptance failures are evidence gaps/diagnostics, not final-gate failures.
- `round_08`: treated as `stage=final`, `final_gate_applicable=true`; final acceptance failures still count.
- Final snapshot still fails CLI end-to-end, cwd-independent CLI, hidden acceptance pytest import, and memory-aware report checks; early rounds are no longer counted as final-gate failures.
