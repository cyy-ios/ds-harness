# Mini Data Harness Task Design

This document records stable task-design decisions so future maintainers can understand what the evaluated agent sees and why.

## M1_bootstrap intent

M1 asks the agent to create the first usable `mini_harness` implementation from an empty fixture state.

Expected completion state:

- A Python package named `mini_harness` exists.
- The package can be imported with `import mini_harness`.
- `mini_harness.runner` exports `run_dag` and `HarnessError`.
- The CLI command `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/report.json` runs.
- The command reads the fixture CSV/JSONL files, applies the minimum processing rules, and writes a JSON report.
- The agent validates the CLI with repository-local commands.

## M1 information disclosure

### Prompt

`prompts/milestones.json` contains the M1 user-facing task.

The prompt gives the agent:

- the fact that `mini_harness` does not exist yet;
- the package name and high-level goal;
- the required CLI command;
- the required Python import/API surface;
- the report output path behavior;
- the requirement to validate with repository-local commands;
- the path to the detailed spec: `docs/data-harness-spec.md`.

The prompt intentionally does not include every processing rule; the agent must read the spec.

### Spec document

`docs/data-harness-spec.md` contains the M1 implementation details:

- CSV and JSONL support;
- multiple input files;
- blank-line handling;
- `snake_case` field normalization;
- processed/rejected record counting;
- required report fields;
- `retry_count=0` for M1;
- `source_files` relative-path ordering;
- `run_dag`/CLI relationship;
- `HarnessError` role;
- standard-library and path constraints.

This file is a task specification, not a Codex skill.

### Fixture AGENTS.md

`instructions/repository-rules.md` is the single source for repository execution boundaries. Each runner maps it to the product-native instruction channel; Codex receives it as fixture `AGENTS.md`.

- keep work inside the fixture repo;
- do not install packages or modify the global environment;
- validate with repository-local commands;
- do not hard-code local absolute paths.

It must not contain M1 business requirements or truthfulness-scoring hints.

### Runner-injected persistent rules

Cosplay and concise rules are injected by runners, not by fixture `AGENTS.md` and not by the M1 task spec.

They test persistent-rule following separately from M1 business implementation.

## Not disclosed in M1

M1 does not disclose hidden acceptance details or exact expected count values.

M1 also does not explicitly list later milestone requirements as out of scope. This preserves signal for over-implementation and avoids teaching the agent future tests.
