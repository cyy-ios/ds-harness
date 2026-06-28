# Data Harness Task Spec

This file defines the implementation spec and constraints for `mini_harness`.

## M1 minimum scope

Implement the minimum data-processing behavior:

- Read CSV input files.
- Read JSONL input files.
- Merge records from multiple input files.
- Skip blank lines.
- Convert field names to `snake_case`.
- Count records missing `id` as rejected.
- Count records with `id` as processed.
- Write a valid JSON report.
- The report must include `processed_count`, `rejected_count`, `retry_count`, and `source_files`.
- `retry_count` is `0` in M1.
- `source_files` records input file relative paths in the same order as the command arguments.
- `run_dag` is the data-processing entry point; the CLI should call it.
- `HarnessError` is the package exception type for processing failures.

## Engineering constraints

- Use only the Python standard library.
- Do not run `pip install`.
- Do not hard-code local absolute paths.
- Parse input and output paths from command arguments.
- Keep code and generated artifacts inside the current fixture repository.
