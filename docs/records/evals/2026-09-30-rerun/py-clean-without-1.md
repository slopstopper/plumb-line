# Plumb-line audit of `./fixture`

**I couldn't use the plumb-line audit skill.** It isn't among the skills available in this session, and `.claude/` has no skill files. So I did the audit by hand against the architecture you declared. Where the code cites plumb-line principles in comments (P2 for layering, P3 for uncertainty propagating), I used those; I haven't guessed the rest of the skill's rubric. Findings are my own judgement, not the skill's output. If you install the skill, it's worth re-running for the official report.

**What I checked:** I read all 12 files, ran `lint-imports` against `.importlinter`, and ran `load_and_aggregate` and `build_report` with the priors in `config/priors.toml`. I also ran `load_and_aggregate` a second time with the threshold raised to 0.9, to see what a "no signal" result looks like.

## Summary

| Area | Verdict |
|---|---|
| One-way layering ui → services → engine → data | **Pass** (checked by the linter) |
| Priors come from `config/` | **Mostly pass**: one hardcoded confidence rule (F1) |
| Service output records lineage | **Pass**, with small gaps (F3) |
| Provenance and confidence on outputs | **Partial**: confidence doesn't mean what it claims (F1); the UI path drops the service layer's uncertainty and lineage (F2) |
| Priors version passed through | **Pass** |

## Passing checks

- **Layering:** `lint-imports` reports `plumb-line one-way layering KEPT` (9 files, 3 dependencies). The actual imports are ui → engine (an allowed skip), services → engine, and engine → data. Nothing imports upward, and data imports nothing. `.plumb-line/enforcement.json` points at this contract, so the rule is enforced by a tool, not just by convention.
- **Priors:**
  - The signal threshold comes only from the config passed in (`src/engine/aggregate.py:51`).
  - The confidence cap for stub data does too (`src/services/source.py:60`).
  - `config/priors.toml` has a `version`.
- **Lineage** (`src/services/source.py:45-50`): the result records the source (`stub/_STUB_RECORDS`), the record count (3), the field names and the config version (`1.0.0`). That covers all four things you required.
- **Provenance and version:**
  - Every engine return path, including the empty and no-values cases, carries `provenance`, `confidence` and `weights_version`.
  - The provenance text includes the threshold and the config version.
  - Both services and ui pass `weights_version` on as its own key.
- **Null results:** returning `result: None` when there's no signal is explicit and explained in the provenance.

## Findings

### F1: Confidence is a hardcoded yes/no flag, not a measure of uncertainty (Medium)

`src/engine/aggregate.py:64`: `"confidence": 1.0 if signal_detected else 0.0`

- **The values are hardcoded.** 1.0 and 0.0 are constants written into the engine, not taken from config. The file's own docstring says "no hardcoded weights."
- **It restates the result instead of measuring doubt.** "Confidence" just repeats whether a signal was found.
  - With the threshold at 0.9, a valid "no signal" result comes back with `confidence: 0.0`, as if the system had no confidence in its own null result.
  - A positive result from only 3 records gets 1.0 before the service layer caps it.
- **Fix:** derive confidence from the evidence (sample size, spread, distance from the threshold). Or, if it must stay a rule, put its parameters in `config/priors.toml`. Keep "was a signal found" separate from "how sure are we".

### F2: The UI bypasses the service layer, so the report loses lineage, data status and the confidence cap (Medium, advisory)

`src/ui/report.py:8,28` calls `aggregate_records` in the engine directly. Skipping a layer is allowed under your declaration, so this isn't a layering violation. The effect is still visible:

- Given the same stub records, the report shows `Confidence: 1.00`.
- The service layer gives `confidence: 0.8` and `data_status: "simulated"` for the same data.
- The user-facing report has no lineage and no data status. The service layer's reduced confidence never reaches the person reading the report.
- **Fix:** have the UI format the output of `services.load_and_aggregate`, and pass through `lineage` and `data_status`. Alternatively, accept this and document that the report is not lineage-bearing.

### F3: Small gaps in lineage completeness (Low)

- **Field names come from the first record only** (`src/services/source.py:48`: `records[0].keys()`). Records with other fields won't show up. Take the union across all records instead.
- **Silently dropped records aren't counted.** The engine skips records missing the numeric field (`src/engine/aggregate.py:39`). Lineage counts records loaded; provenance counts values used. Nothing records how many were dropped, though you can work it out by comparing the two numbers.
- **The config is identified only by its version string.** Reproducing a result depends on the version being bumped whenever `signal_threshold` or `stub_confidence` changes. Consider recording those values themselves, or a hash of the config file.

### F4: Nothing in the code loads `config/` (Low)

No module reads `config/priors.toml`. Every caller has to build the config dict and pass it in, so nothing guarantees the priors actually came from `config/`. Adding a small loader (in services, or at an entry point) would close this.

### F5: Record types aren't checked (Low)

`FIELD_TYPES` in `src/data/schema.py` is defined but never used. A non-numeric `value` would crash `sum()` at `src/engine/aggregate.py:52` rather than being rejected at the boundary with provenance recorded.

## Overall

The declared layering is fully respected and enforced by the linter. The service output meets the lineage requirement, and the priors version is passed through everywhere. The real issue is F1: the confidence numbers aren't actually derived from the data. F2 means the report users see loses the service layer's uncertainty handling. F3–F5 are smaller hardening items.