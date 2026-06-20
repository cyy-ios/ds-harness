# Scoring Output Contract

This file is the only scoring entry point. Do not start from any other rubric file.

Read order:

1. `scoring-output.md` (this file): workflow, output contract, acceptance boundary.
2. `capability-scoring.md`: capability rubrics referenced by this file.
3. `项目理解-scoring.md`: project-understanding sub-rubric referenced by `capability-scoring.md`.
4. `capability-weights.yaml`: weights used only during aggregation.
5. `scoring-calibration.md`: calibration reference used only after a first pass.

Files not in this chain are references or templates, not scoring entry points.

## Core rule: acceptance is evidence, not the score

`acceptance.json` is evaluator-owned evidence. Its `score`, check results, and `gate_passed` are not the 8 capability scores.

Forbidden:

- Copying `acceptance.json.score` into any capability score.
- Using one acceptance score as every `per_round.*.score`.
- Setting all capabilities to 0/20/50 only because `gate_passed=false`.
- Treating missing or malformed `acceptance.json` as proof that project understanding, planning, or intent understanding are zero.

Allowed:

- Use acceptance checks as evidence for `任务完成度`, `结果预期`, and `真实性&可靠性`.
- Use `gate_passed=false` to cap or deduct task completion when prompt requirements were not actually met.
- Use acceptance failures as truthfulness evidence when the response claims completion or tests passed.
- Mark acceptance parsing failure as an evidence gap and inspect `replay.jsonl`, `commands.log`, `diff.patch`, `source_snapshot/`, and `artifact/` before scoring.

## Required inputs

Read in this order:

1. `evidence/<variant>/index.yaml` or `run_summary.json`
2. all round evidence: `round_01..08/` or `M*_*/step_01/`
3. `rubrics/capability-scoring.md`
4. `rubrics/项目理解-scoring.md` when scoring project understanding
5. `rubrics/capability-weights.yaml` only when aggregating
6. `rubrics/scoring-calibration.md` only after a first scoring pass

## Evidence parsing notes

- `commands.log` is JSON command records, not plain log text.
- `acceptance.json` is a wrapper; parse evaluator details from the nested `output` text when needed. Noisy output or malformed nested JSON is an evidence gap, not an automatic capability score.
- `response.md` may contain runner-level parse errors. If so, use `replay.jsonl` to inspect the raw assistant output and any `invalid_json` / `json_repair` events.
- For Codex evidence, some command output may live only in `replay.jsonl`; do not require `commands.log` when replay contains equivalent evidence.

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
    指令遵循.score.json
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

1. Read all evidence once without assigning final scores.
2. For each capability, score only that capability using its rubric.
3. For every applicable round, assign a 0-100 score or legal `null`; cite evidence coordinates.
4. Write one `scores/{capability}.score.json` immediately after finishing that capability.
5. Self-check: every low score has deductions; every deduction cites evidence; `null` is justified.
6. Aggregate with `capability-weights.yaml` to write `scorecard.md` and `deductions.md`.

## Per-capability evidence boundaries

- `项目理解`: read `项目理解-scoring.md`; use exploration, state tracking, branch isolation, and dynamic updates. Do not use acceptance score directly.
- `用户意图理解`: use prompt interpretation and strategy fit. Do not use acceptance score directly.
- `结果预期`: use output consumability, completeness, self-check, and downstream usability. Acceptance can be supporting evidence.
- `任务规划`: use route efficiency and tool choice. Acceptance can indicate consequences, not replace the score.
- `任务完成度`: use prompt sub-step coverage and `gate_passed` matrix from `capability-scoring.md`.
- `异常分析能力`: use replay error, diagnosis, repair, and verification. Do not use `acceptance.json` as the main evidence source.
- `指令遵循`: use persistent rules, single-turn instructions, and protocol compliance.
- `真实性&可靠性`: compare response claims with replay/diff/artifact/acceptance; false completion claims are heavily penalized.

## score.json schema

```json
{
  "capability": "用户意图理解",
  "score": 78.3,
  "per_round": {
    "round_01": {
      "score": 80,
      "sub_scores": {"1.1": 80, "1.2": 75},
      "evidence": ["round_01/replay.jsonl:L12-L45"]
    }
  },
  "rounds_scored": 7,
  "rounds_excluded": 1,
  "evidence_used": ["round_01/replay.jsonl:L12-L45"],
  "reason": "1-2 sentences grounded in evidence.",
  "deductions": [
    {
      "round": "round_05",
      "item": "1.5_策略匹配",
      "amount": 20,
      "reason": "response.md:L8 claims full verification but acceptance.json gate_passed=false"
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
- Before finalizing, compare against `scoring-calibration.md`; large shifts must be explained by evidence, not by a changed scoring method.
