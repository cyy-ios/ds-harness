# Deductions

- M1-M4: diagnostic acceptance records `No module named mini_harness` for hidden CLI/source-layout checks before M8 added `src/mini_harness`; not copied as capability scores.
- M5: cwd support was eventually fixed, but replay shows ineffective `sitecustomize.py` attempts before the forwarding package solution.
- M8: final gate passes, but source-layout compatibility arrived late and cumulative diffs contain tmp report artifacts.
- Runner limitation: native runner accepts `--model gpt-5.5` but has no explicit reasoning-effort flag; medium came from user Codex config.
