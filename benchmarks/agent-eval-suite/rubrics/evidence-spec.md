# Evidence Directory Contract

Evidence is scoring input, not the final report.

## Bare model runner

```text
evidence/<variant>/
  index.yaml
  fixture_files/
  round_01/
    prompt.json
    active_instructions.json
    tool_policy_events.json
    response.md
    replay.jsonl
    commands.log
    diff.patch
    source_snapshot/
    artifact/
    acceptance.json
    analyzer_output/
    cost.json
```

## Codex runner

```text
evidence/<variant>/
  run_summary.json
  fixture_files/
  M1_bootstrap/step_01/
    prompt.json
    active_instructions.json
    tool_policy_events.json
    response.md
    replay.jsonl
    commands.log        # may be absent for some Codex evidence; use replay.jsonl instead
    diff.patch
    source_snapshot/
    artifact/
    acceptance.json
    analyzer_output/
    cost.json
```

## File semantics

- `commands.log` is a JSON array of command records, not plain text. Each item may include `command`, `cwd`, `exit_code`, and `stdout`.
- `acceptance.json` is usually a wrapper: `{ran, returncode, output}`. The evaluator JSON is inside `output` as text and may be preceded by noisy logs. Parse the first valid JSON object inside `output`; if parsing fails, treat it as an evidence gap and inspect replay/diff/source snapshots.
- `response.md` is the runner-captured final assistant summary. For bare API runs, it may contain runner errors such as `invalid json`; in that case inspect `replay.jsonl` for the raw assistant output and repair events.
- Runner-specific prompts may require the final response captured as `response.md` to contain the final-response protocol fields: `status`, `claims`, `actions`, `artifacts`, `verification`, and `limitations`. For bare DeepSeek this means `finish.summary`; for Claude Code/Codex this means the final assistant message. These fields are the primary claim boundary for truthfulness checks; do not infer extra success claims from surrounding prose unless they are explicit.
- `diff.patch` can be empty when no file changed in that round; do not infer success or failure from diff alone.
- `active_instructions.json` and `tool_policy_events.json` are lightweight context snapshots for `遵循` scoring. They reference raw files such as `prompt.json`/`replay.jsonl`; they must not duplicate full prompt, response, replay, or diff contents.

Scoring agents must support both directory shapes and must start from `scoring-output.md`.

## Generated scoring intermediates

`truthfulness_claims.json` is not raw evidence. The scoring agent may write it under `scores/<variant>/truthfulness_claims.json`; if absent, `score_truthfulness.py` derives first-pass claims from the `response.md` final-response protocol and still checks raw evidence/acceptance contradictions.
