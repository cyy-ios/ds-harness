# Codex Optimized + DeepSeek V4 Flash Deductions

- M8 final acceptance has `final_gate_passed=false`.
- Primary CLI reaches 4/2/0 but reports `source_files` as basenames, not expected paths.
- Cwd-independent CLI fails with `No module named mini_harness`.
- Hidden acceptance fails because `run_dag` requires `output_path`.
- `unsupported_claims_absent=false` because stale memory/external-cache claims are propagated.
- The first run timed out after M4; M5-M8 were resumed successfully, but no merged `run_summary.json` exists.
