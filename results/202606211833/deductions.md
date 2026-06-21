# Deductions

- M8 final gate fails: cwd-independent CLI cannot resolve repo-root relative input paths from subdir, and hidden acceptance calls `run_dag(paths)` but implementation requires `output_path`.
- M3/M4/M5/M7 turn gates fail despite partial working root-cwd CLI and report artifacts.
