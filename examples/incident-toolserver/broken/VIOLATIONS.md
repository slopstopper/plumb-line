# Answer key — planted violations in `broken/toolserver.mjs`

This variant is the reconstruction's *incident state*: the violations are the
point, and an audit of this directory should find them, not treat them as
regressions. See `../README.md` for the incident being modeled.

| ID | Where | Violation |
| --- | --- | --- |
| P4 | `spawnWorker`, `orchestrateTasks`, `storeMemory` | Unquarantined fakery — stubs return success-shaped payloads that are indistinguishable from real results at every call site |
| P4 | status report aggregation | Mock results enter a real output path (the health summary) with no label and no opt-in |
| P3 | all tool returns | No provenance or confidence travels with any result; the report cannot say what it rests on |
| P6 | whole file | No maturity vocabulary — nothing distinguishes `current` tools from `mock` ones, so the tool surface overstates the tool reality |

The `instrumented/` variant resolves the P3/P4 findings via the provenance
primitive and is the corrective-action half of the demo. It deliberately keeps
the stubs (quarantine labels fakery; it does not delete it) — a maturity label
per tool (P6) would be the next step in a real adoption, not shown here.
