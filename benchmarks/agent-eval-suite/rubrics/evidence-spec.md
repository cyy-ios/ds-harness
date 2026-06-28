# Evidence Directory Contract

Evidence is scoring input, not the final report.

## Contract

New runs collect only the new evidence contract:

```text
evidence/<variant>/
  index.json or run_summary.json
  <milestone>/step_01/
    tool_events.jsonl
    result.json
```

Flat bare-run rounds may use `round_01/` instead of `<milestone>/step_01/`, but the file set is the same.

## File semantics

- `tool_events.jsonl` is the only per-round tool/action evidence. Each line is a JSON object with `kind` (`tool_call` or `tool_result`), `tool`, `call_id`, `arguments` or `output`, and optional timing/error fields.
- `result.json` is the only per-round result evidence. It contains `milestone`, `runner`, `final_response`, and parsed `response_protocol` fields: `status`, `claims`, `actions`, `artifacts`, `verification`, and `limitations`.
- Do not write any other per-round raw evidence files in new runs.
- If a future scorer needs more evidence, add it explicitly to this contract instead of reviving legacy files implicitly.

## Generated scoring intermediates

Scoring scripts may write derived files such as `instruction_checklist_results.json`, `score_expected_tools.json`, `score_concise.json`, `score_cosplay.json`, `truthfulness_claims.json`, and `mechanized-overrides.json`. These are not raw evidence.
