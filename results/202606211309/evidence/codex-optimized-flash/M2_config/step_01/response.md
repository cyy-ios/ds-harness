Let me read all existing implementation files to understand the current state.
Now I have a full picture of the codebase. Let me verify the implementation works and check for any issues.
JSON config works. There's a bug in the YAML parser — `_yaml_parse_list` expects 2 return values from `_yaml_parse_list_item` but gets 3. Let me fix that.
Now let me test CLI overrides and verify report content.
All three scenarios work. Let me check the existing tests and the pyproject.toml path issue.
Let me clean pycache and run all verification scenarios.
All four scenarios pass. Let me verify the report contents have the required fields.
All reports contain the required fields. Let me verify the module exports and API surface.
Let me do one final clean verification — confirm no pycache was left behind and the YAML report has correct content.
No pycache remaining. Here's a summary of what's done and verified:

---

## Completed

**Package created:** `mini_harness` at the fixture repo root with 4 modules:

| Module | File | Role |
|---|---|---|
| `__init__.py` | Exports `run_dag` & `HarnessError` | Package entry |
| `__main__.py` | `python -m mini_harness` dispatch | Module runner |
| `cli.py` | `argparse` with `run` subcommand | CLI entry |
| `runner.py` | `extract → clean → report` DAG | Data processing |
| `config.py` | JSON + stdlib-only YAML parser | Config loading |

**CLI `run` subcommand supports:**
- `--config` / `-c` — optional JSON or YAML config file
- `sources` — optional positional file list (overrides config)
- `--output` / `-o` — optional output path (overrides config)

**Config merge logic:** CLI sources/output beat config; config fills gaps when CLI flags are absent.

**Verified scenarios (all passing):**

| Scenario | Command | Result |
|---|---|---|
| Basic | `python -m mini_harness run data/input.csv data/events.jsonl --output tmp/verify_basic.json` | 4 processed, 2 rejected |
| JSON config | `python -m mini_harness run --config tmp/test_config.json` | 2 processed, 1 rejected |
| YAML config | `python -m mini_harness run --config tmp/test_config.yaml` | 4 processed, 2 rejected |
| CLI override | `python -m mini_harness run data/events.jsonl --config tmp/test_config.json --output tmp/verify_override.json` | 2 processed, 1 rejected |

**Bug fixed:** YAML parser `_yaml_parse_list` unpacked 2 return values from `_yaml_parse_list_item` (which returns 3) — patched to unpack all 3.

**Report fields verified:** `processed_count`, `rejected_count`, `retry_count`, `source_files`, `rejects`, `logs` (with `attempt`/`stage`/`status`), `memory_reference` — all present.