# Harness base decision

## Decision

Use Codex as the DeepSeek harness base. The goal is long-term task completion quality, reliability, and daily usability, not the fastest experimental skeleton.

Keep Codex tool safety, agent loop, persistent state, recovery, events, and test structure. Adapt only the model/provider boundary, context assembly, and tool-call feedback needed for DeepSeek. Deterministic constraints should enter stable implementation only after repeatable evaluation gains.

## Cost

Codex is larger and slower to adapt, but its runtime gives a higher long-term ceiling. The extra cost is accepted because DS Harness evaluates full agent behavior, not only API connectivity.

## Alternatives not selected

| Project | Useful ideas | Why not base |
| --- | --- | --- |
| Reasonix | Clear modules; evidence/checkpoint/planner-executor separation. | More constrained; weaker production runtime and long-term ceiling. |
| CodeWhale | LSP, loop guards, rollback, background task feedback. | Rule interventions may add noise and suppress model judgment. |
| CoreCoder | Short control flow and easy auditing. | Experimental skeleton; lacks validation, safety, recovery, state, and observability. |
| deepcode-cli | DeepSeek thinking, parameter mapping, Skills/MCP connection. | Mostly provider/interaction layer; not a full harness. |
| Aider | Repo map, Git workflow, multi-model support. | Useful coding baseline, not a DeepSeek-native harness base. |
| Cline | IDE/CLI/SDK and provider ecosystem. | Useful workflow reference, not the harness base. |

Other projects may provide candidate mechanisms, but each mechanism must pass the unified evaluation before becoming stable.
