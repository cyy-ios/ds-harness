# Scoring Output Contract

This file is the only scoring entry point. Do not start from any other rubric file.

Read order:

1. `scoring-output.md` (this file): workflow, output contract, acceptance boundary.
2. `capability-scoring.md`: capability rubrics referenced by this file.
3. `项目理解-scoring.md`: project-understanding sub-rubric referenced by `capability-scoring.md`.
4. `capability-weights.yaml`: weights used only during aggregation.
5. `scoring-calibration.md`: pre-score calibration protocol; pass calibration before scoring a new run.

Files not in this chain are references or templates, not scoring entry points.

## Core rule: acceptance is evidence, not the score

`result.json` is evaluator-owned evidence. Its `score`, check results, `turn_gate_passed`, `diagnostic_gate_passed`, and `final_gate_passed` are not the 8 capability scores.

Forbidden:

- Copying `result.json.score` into any capability score.
- Using one acceptance score as every `per_round.*.score`.
- Setting all capabilities to 0/20/50 only because `gate_passed=false`, `turn_gate_passed=false`, or `final_gate_passed=false`.
- Treating missing or malformed `result.json` as proof that project understanding, planning, or intent understanding are zero.

Allowed:

- Use acceptance checks as evidence for `任务完成度`, `结果预期`, and `真实性&可靠性`.
- Use `turn_gate_passed` as prompt-specific completion evidence for the current round; inspect `turn_failed_checks` and manual evidence before scoring.
- Use `final_gate_passed=false` to cap or deduct final-round task completion only when `final_gate_applicable=true`; otherwise treat `diagnostic_gate_passed`/`core_gate_passed` as diagnostic evidence.
- Use acceptance check failures as truthfulness evidence when the response claims the failed check passed; use final gate failure as completion-claim evidence only when `final_gate_applicable=true`.
- Mark acceptance parsing failure as an evidence gap and inspect `tool_events.jsonl`, `tool_events.jsonl`, `tool_events.jsonl`, `result.json`, and `result.json` before scoring.

## Required inputs

Read in this order:

1. `evidence/<variant>/index.json` or `run_summary.json`
2. all round evidence: `round_01..08/` or `M*_*/step_01/`
3. `rubrics/capability-scoring.md`
4. `rubrics/项目理解-scoring.md` when scoring project understanding
5. `rubrics/capability-weights.yaml` only when aggregating
6. `rubrics/scoring-calibration.md` before scoring; calibration must pass within ±3 before new-run scoring
7. Mechanized score files (if they exist, read and use as-is; do not re-judge):
   - `evidence/<variant>/score_cosplay.json` — deterministic cosplay scores per round
   - `evidence/<variant>/score_concise.json` — deterministic concise scores per round
   - `evidence/<variant>/score_expected_tools.json` — deterministic tool selection scores per round

## Evidence parsing notes

- `tool_events.jsonl` is JSON command records, not plain log text.
- `result.json` is a wrapper; parse evaluator details from the nested `output` text when needed. Prefer `turn_gate_passed` for the current prompt and `final_gate_passed` only for final-round full acceptance. Noisy output or malformed nested JSON is an evidence gap, not an automatic capability score.
- `result.json` may contain runner-level parse errors. If so, use `tool_events.jsonl` to inspect the raw assistant output and any `invalid_json` / `json_repair` events.
- For Codex evidence, some command output may live only in `tool_events.jsonl`; do not require `tool_events.jsonl` when replay contains equivalent evidence.

## Output layout

Single variant:

```text
results/<timestamp>/
  evidence/<variant>/
  scores/
    项目理解.score.json
    用户意图理解.score.json
    结果预期.score.json
    任务规划.score.json
    任务完成度.score.json
    异常分析能力.score.json
    遵循.score.json
    真实性&可靠性.score.json
  scorecard.md
  deductions.md
```

Multiple variants:

```text
results/<timestamp>/
  evidence/<variant>/
  scores/<variant>/
    *.score.json
    scorecard.md
    deductions.md
  scorecard.md
  deductions.md
```

## Scoring workflow

1. Run the `scoring-calibration.md` procedure: independently rescore `results/202606211740` and match every capability plus overall within ±3 before assigning any new-run scores.
2. Read all evidence once without assigning final scores.
3. For each capability, score only that capability using its rubric.
4. For every applicable round, assign a 0-100 score or legal `null`; cite evidence coordinates.
5. Write one `scores/{capability}.score.json` immediately after finishing that capability. For truthfulness, use the `result.json` final-response protocol as the claim boundary; optionally pass `--claims-file scores/<variant>/truthfulness_claims.json`, or omit it so `score_truthfulness.py` derives claims from the protocol.
6. Self-check: every low score has deductions; every deduction cites evidence; `null` is justified.
7. Record in the scorecard that calibration against `results/202606211740` passed within ±3, or do not finalize the score.
8. Aggregate with `capability-weights.yaml`: compute the weighted base score from non-multiplier capabilities, then multiply by `真实性&可靠性` and `遵循` coefficients to write `scorecard.md` and `deductions.md`.

## Per-capability evidence boundaries

- `项目理解`: read `项目理解-scoring.md`; use exploration, state tracking, branch isolation, and dynamic updates. Do not use acceptance score directly.
- `用户意图理解`: use prompt interpretation and strategy fit. Do not use acceptance score directly.
- `结果预期`: use output consumability, completeness, self-check, and downstream usability. Acceptance can be supporting evidence.
- `任务规划`: use route efficiency and tool choice. **工具选择 is mechanized**: read `score_expected_tools.json`; use per-round values as-is; do not re-judge. Acceptance can indicate consequences, not replace the score.
- `任务完成度`: use prompt sub-step coverage and the turn/final gate matrix from `capability-scoring.md`; non-final `diagnostic_gate_passed`/`core_gate_passed` is diagnostic only; `turn_gate_passed` is the prompt-specific gate.
- `异常分析能力`: use replay error, diagnosis, repair, and verification. Do not use `result.json` as the main evidence source.
- `遵循`: **fully mechanized**. Run `score_following.py`; it reads task-authored `instruction-checklist.json` plus `score_cosplay.json` and `score_concise.json`, writes `遵循.score.json`, and does not use prompt-regex requirement extraction. Do not hand-score or override sub-scores.
- Truthfulness: use `result.json` protocol fields (`status`, `claims`, `actions`, `artifacts`, `verification`, `limitations`) as the first claim boundary; optional `truthfulness_claims.json` may refine verdicts. Compare claims with `tool_events.jsonl` and `result.json` evidence; false completion claims are heavily penalized. A runner/API error message alone is not a completion claim.

## score.json schema

```json
{
  "capability": "用户意图理解",
  "score": 78.3,
  "per_round": {
    "round_01": {
      "score": 80,
      "sub_scores": {"1.1": 80, "1.2": 75},
      "evidence": ["round_01/tool_events.jsonl:L12-L45"]
    }
  },
  "rounds_scored": 7,
  "rounds_excluded": 1,
  "evidence_used": ["round_01/tool_events.jsonl:L12-L45"],
  "reason": "1-2 sentences grounded in evidence.",
  "deductions": [
    {
      "round": "round_05",
      "item": "1.5_策略匹配",
      "amount": 20,
      "reason": "result.json:L8 claims full verification but final acceptance evidence fails"
    }
  ],
  "evidence_gaps": []
}
```

## Hard constraints

- `round` must be `round_NN` or the matching milestone name.
- `item` must cite a rubric sub-item id or name.
- `amount` is 5-100 in steps of 5.
- `reason` must cite evidence coordinates; no vague judgement.
- Capability scores below 80 must have deductions.
- `scorecard.md` is overview; `deductions.md` is factual deduction detail only.
- Before scoring, complete the `scoring-calibration.md` ±3 calibration against `results/202606211740`; do not use the calibration run as a direct band rule for the target run.
