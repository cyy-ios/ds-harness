# DeepSeek V4 Pro Deductions

- `round_01..03/acceptance.json`: evaluator-owned acceptance score is 20/100 and `gate_passed=false`; CLI entry and hidden acceptance fail.
- `round_04..06/acceptance.json`: captured acceptance output has no usable score/gate fields, so these rounds are treated as evidence gaps.
- `round_08/acceptance.json`: evaluator-owned acceptance score is 10/100 and `gate_passed=false`; final completion fails.
- `round_08/replay.jsonl`: no valid finish event/response.md captured.
- Model repeatedly reported local pytest success while acceptance showed core task failure.
