# Model Scoreboard

Scores for model or model+harness combinations under the current DS Harness scoring system. Current table uses the calibrated rubric: before scoring a target run, the scoring agent must calibrate against `results/202606211740` within +/-3 for every capability and overall.

## Codex Native + GPT-5.5 Medium / Official Codex CLI

- Run: `results/202606211623`
- Mode: Official Codex CLI native variant, model `gpt-5.5`, reasoning effort medium from Codex config
- Overall: **83.5**

| Capability | Score |
| --- | ---: |
| Project understanding | 84.0 |
| User intent understanding | 86.0 |
| Expected result fit | 82.0 |
| Task planning | 74.0 |
| Task completion | 90.0 |
| Exception analysis | 86.0 |
| Instruction following | 80.0 |
| Truthfulness & reliability | 84.0 |

Notes: Independent main-agent score. M8 final gate passes. GPT-5.5 also passes all eight prompt-specific turn gates in local calibration smoke.

---

## Codex Unoptimized + DeepSeek V4 / Official Codex CLI via proxy

- Run: `results/202606211142`
- Mode: Official Codex CLI + DeepSeek proxy, without ds-codex provider adaptation
- Overall: **80.0**
- Score source: `scores/codex-unoptimized/turn-gate-calibrated/`

| Capability | Score |
| --- | ---: |
| Project understanding | 80.0 |
| User intent understanding | 78.0 |
| Expected result fit | 78.0 |
| Task planning | 70.0 |
| Task completion | 91.0 |
| Exception analysis | 72.0 |
| Instruction following | 84.0 |
| Truthfulness & reliability | 80.0 |

Notes: Turn-gate calibrated rescore v2. Per-round states were reconstructed from fresh fixture plus each cumulative diff.patch to avoid final-state pollution. M1/M2/M3/M5/M6/M7/M8 turn gates pass; M4 fails `m4_noise_cli`; M8 full final gate passes.

---

## Codex Unoptimized + DeepSeek V4 Flash / Official Codex CLI via proxy

- Run: `results/202606211236`
- Mode: Official Codex CLI + DeepSeek proxy, proxy-side `DEEPSEEK_MODEL=deepseek-v4-flash`, without ds-codex provider adaptation
- Overall: **80.0**
- Score source: `scores/codex-unoptimized-flash-calibrated-211740/`

| Capability | Score |
| --- | ---: |
| Project understanding | 80.0 |
| User intent understanding | 78.0 |
| Expected result fit | 80.0 |
| Task planning | 68.0 |
| Task completion | 90.0 |
| Exception analysis | 72.0 |
| Instruction following | 82.0 |
| Truthfulness & reliability | 82.0 |

Notes: Calibrated against `results/202606211740` within +/-3 before target scoring. M8 final gate passes all checks; M1/M2/M3/M5/M6/M7/M8 turn gates pass and M4 fails `m4_noise_cli`.

---

## Codex Optimized + DeepSeek V4 Pro / ds-codex provider

- Run: `results/202606211350`
- Mode: ds-codex optimized DeepSeek provider, model `deepseek-v4-pro`
- Overall: **76.5**
- Score source: `scores/codex-optimized-pro-calibrated-211740/`

| Capability | Score |
| --- | ---: |
| Project understanding | 78.0 |
| User intent understanding | 76.0 |
| Expected result fit | 76.0 |
| Task planning | 62.0 |
| Task completion | 86.0 |
| Exception analysis | 74.0 |
| Instruction following | 76.0 |
| Truthfulness & reliability | 78.0 |

Notes: Calibrated against `results/202606211740` within +/-3 before target scoring. M8 final gate passes; only memory-aware report remains failed, with minor log-artifact noise.

---

## DeepSeek V4 Pro / Bare API

- Run: `results/202606202320`
- Mode: Bare API + simplified tool loop
- Overall: **64.3**
- Score source: `scores/deepseek-v4-pro-calibrated-211740/`

| Capability | Score |
| --- | ---: |
| Project understanding | 54.0 |
| User intent understanding | 61.0 |
| Expected result fit | 55.0 |
| Task planning | 66.0 |
| Task completion | 68.0 |
| Exception analysis | 75.0 |
| Instruction following | 76.0 |
| Truthfulness & reliability | 58.0 |

Notes: Calibrated against `results/202606211740` within +/-3 before target scoring. Early rounds are prompt-turn evidence, not final-gate failures; final snapshot still fails cwd-independent CLI, hidden acceptance pytest import, and memory-aware report.

---

## Codex Optimized + DeepSeek V4 Flash / ds-codex provider

- Run: `results/202606211309`
- Mode: ds-codex optimized DeepSeek provider, model `deepseek-v4-flash`
- Overall: **61.0**
- Score source: `scores/codex-optimized-flash-calibrated-211740/`

| Capability | Score |
| --- | ---: |
| Project understanding | 70.0 |
| User intent understanding | 68.0 |
| Expected result fit | 54.0 |
| Task planning | 64.0 |
| Task completion | 58.0 |
| Exception analysis | 66.0 |
| Instruction following | 70.0 |
| Truthfulness & reliability | 48.0 |

Notes: Calibrated against `results/202606211740` within +/-3 before target scoring. Final gate fails, but replay shows more sustained implementation work than CC+DS Flash; deductions remain for cwd import, hidden API, source files, and unsupported claims.

---

## Claude Code CLI + DeepSeek V4 Pro / Anthropic-compatible API

- Run: `results/202606211833`
- Mode: Claude Code CLI itself routed to DeepSeek Anthropic-compatible API, model `deepseek-v4-pro`
- Overall: **60.9**
- Score source: `scores/claude-deepseek-v4-pro-calibrated-211740/`

| Capability | Score |
| --- | ---: |
| Project understanding | 64.0 |
| User intent understanding | 63.0 |
| Expected result fit | 60.0 |
| Task planning | 61.0 |
| Task completion | 58.0 |
| Exception analysis | 68.0 |
| Instruction following | 60.0 |
| Truthfulness & reliability | 58.0 |

Notes: Calibrated against `results/202606211740` within +/-3 before target scoring. M1/M2/M6 turn gates pass, and final package/root CLI/config/M4/memory checks pass; M8 final gate still fails on cwd-independent CLI and hidden acceptance pytest.

---

## Claude Code CLI + DeepSeek V4 Flash / Anthropic-compatible API

- Run: `results/202606211702`
- Mode: Claude Code CLI itself routed to DeepSeek Anthropic-compatible API, model `deepseek-v4-flash`
- Overall: **48.9**
- Score source: `scores/claude-deepseek-v4-flash-calibrated-211740/`

| Capability | Score |
| --- | ---: |
| Project understanding | 55.0 |
| User intent understanding | 54.0 |
| Expected result fit | 47.0 |
| Task planning | 53.0 |
| Task completion | 38.0 |
| Exception analysis | 64.0 |
| Instruction following | 42.0 |
| Truthfulness & reliability | 48.0 |

Notes: Calibrated against `results/202606211740` within +/-3 before target scoring. Similar final-gate failure pattern to the calibration anchor; 211702 has fuller M6/M7 responses than 211740 but worse package-layout evidence.

---

## DeepSeek V4 Flash / Bare API

- Run: `results/202606202251`
- Mode: Bare API + simplified tool loop
- Overall: **43.7**
- Score source: `scores/deepseek-v4-flash/corrected/turn-gate-calibrated/`

| Capability | Score |
| --- | ---: |
| Project understanding | 42.3 |
| User intent understanding | 38.6 |
| Expected result fit | 38.0 |
| Task planning | 60.0 |
| Task completion | 30.0 |
| Exception analysis | 45.0 |
| Instruction following | 42.5 |
| Truthfulness & reliability | 52.0 |

Notes: Turn-gate calibrated rescore from preserved evidence; original `acceptance.json` files are preserved. Repeated prompt-specific turn gates fail and final snapshot still fails CLI, cwd-independent CLI, hidden acceptance import, and memory report.

## Inclusion rule

Only add a run here when:

- it is under root `results/<timestamp>/`;
- it has `evidence/`, `scores/`, `scorecard.md`, and `deductions.md`;
- scoring followed `benchmarks/agent-eval-suite/rubrics/scoring-output.md`;
- acceptance/gate was used only as evidence, not copied as capability scores;
- `python scripts/verify_results_layout.py` passes.
