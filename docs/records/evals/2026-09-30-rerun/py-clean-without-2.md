# Plumb-line audit: `./fixture`

**How this was run:** there is no plumb-line audit skill in this session. None is registered, and `.claude/` holds no skills. I did the audit by hand against the architecture you declared and the principles the fixture itself cites (P2 one-way layering, P3 uncertainty propagation). I read all 12 files, ran `lint-imports` with the fixture's own contract, and ran the pipeline using `config/priors.toml`. No files were changed.

## Verdict

**The structure holds; there are findings about honest confidence.** The layering, lineage, priors-from-config and version propagation requirements are all met. The problems are in what the confidence numbers say: one path reports more confidence than its data supports, and the engine's confidence value doesn't actually measure confidence.

## Conformance to the declared architecture

| Requirement | Status | Evidence |
|---|---|---|
| One-way layering ui → services → engine → data, skips allowed | ✅ Pass | Imports: `ui→engine` (`src/ui/report.py:8`, an allowed skip), `services→engine` (`src/services/source.py:8`), `engine→data` (`src/engine/aggregate.py:7`). `data` imports nothing. `lint-imports`: **1 kept, 0 broken** (9 files, 3 dependencies). |
| Enforcement is wired up | ✅ Pass | `.importlinter` layer order matches what you declared. `.plumb-line/enforcement.json` points at it. The import-linter `layers` contract allows downward skips, which matches your rule. |
| Priors come from `config/` | ✅ Pass (with a gap, F5) | The threshold comes from the injected config (`aggregate.py:51`). The simulated-data cap comes from `config["stub_confidence"]` (`source.py:60`). There are no hardcoded weights. |
| Service result records lineage (source, record count, field names, config version) | ✅ Pass | `source.py:45-50` has all four. At runtime: `{'source': 'stub/_STUB_RECORDS', 'record_count': 3, 'field_names': [...4 fields], 'config_version': '1.0.0'}`. |
| Outputs carry provenance and confidence | ✅ Present (quality issues: F1, F2) | Engine, service and ui outputs all return both keys, including the early-return branches in the engine. |
| Priors version is propagated | ✅ Pass | `weights_version` is on every engine return (including `aggregate.py:35,48`), passed through by the service (`source.py:63`), and exposed by the ui as a structured key, not only as text (`report.py:48`). |

## Findings

### F1: The ui path skips the service layer and reports higher confidence for the same simulated data (medium)
`src/ui/report.py:28` calls `aggregate_records` directly. The skip itself is allowed, but it also skips everything the service adds on top of the engine result:
- the `stub_confidence` cap (P3)
- `data_status: 'simulated'`
- `lineage`

Result on the same three stub records: the **service reports confidence 0.8, status `simulated`**, while the **ui reports `Confidence: 1.00`** with no simulated flag and no lineage. The only output that carries lineage is not the one the user sees, and the displayed confidence is higher than the service's.
**Fix:** have `build_report` take the service result (a `services→ui` data flow, with ui calling `load_and_aggregate`). Show `data_status` and a summary of the lineage in the report. Otherwise the ui has to repeat the cap itself.

### F2: Engine confidence is just a copy of the signal flag, not a measure of uncertainty (medium)
`aggregate.py:64`: `"confidence": 1.0 if signal_detected else 0.0`. Two consequences:
- A clean "no signal" result, which the engine's own docstring calls valid, is reported with **confidence 0.0**. That reads as "we don't know" when it actually means "we are confident there is nothing". With threshold 0.8 the service returns `result=None, confidence=0.0` even though all three records were read without problems.
- A mean of 0.6501 against a threshold of 0.65, from 1 record, gets confidence 1.0.

The literals 1.0 and 0.0 are really uncalibrated numbers that behave like priors, but they aren't in `config/`.
**Fix:** base confidence on the evidence, e.g. sample size and distance from the threshold, with any constants moved into `priors.toml`. Keep "no signal" and "low confidence" as separate things.

### F3: Records missing the numeric field are dropped silently, and provenance hides it (low)
`aggregate.py:39` filters out records that lack `value`. Provenance says `over {len(values)} records` (`aggregate.py:60`), which counts values used, not records received, while the service lineage records `len(records)`. If 2 of 3 records were missing `value`, the output would say "over 1 records" and lineage would say `record_count: 3`, and nothing would flag the difference.
**Fix:** report both counts (`used N of M records`) and lower confidence when records are dropped.

### F4: `field_names` in the lineage comes from the first record only (low)
`source.py:48`: `list(records[0].keys())`. If records have different fields, the lineage is incomplete. That breaks the promise that the lineage is enough to reproduce the result.
**Fix:** take the union of keys across all records (sorted), or validate against `FIELD_TYPES` and record the schema instead.

### F5: Nothing actually loads `config/priors.toml` (low / informational)
Config is injected everywhere, which is correct, but nothing in `src/` reads the file (`grep` found no loader). So "priors come from `config/`" is a convention the code can't check. Also, the lineage records only `config_version`, so two different `priors.toml` files that share `version = "1.0.0"` would produce identical lineage.
**Fix:** add one loader at the composition root. Consider recording a content hash of the priors file alongside the version.

### F6: Docstrings don't match the code (informational)
- `source.py:29` documents config as `'version'` and `'signal_threshold'` only, but `stub_confidence` is required (`source.py:60`; it raises `KeyError` if missing, which at least fails loudly).
- `report.py:4-5` says the ui may import "engine only". That's narrower than your declared rule and would push the fix for F1 the wrong way. Update it to match the declared direction.

## Summary

| # | Finding | Severity |
|---|---|---|
| F1 | ui skips services and shows 1.00 confidence with no lineage for simulated data | Medium |
| F2 | Engine confidence is the signal flag; a valid null result reads as zero confidence | Medium |
| F3 | Records dropped silently; provenance count doesn't match lineage count | Low |
| F4 | Lineage `field_names` taken from the first record only | Low |
| F5 | No priors loader; lineage records the version but not the content | Low |
| F6 | Docstrings don't match config requirements or the declared layering | Info |

To get the official skill-based audit, install the plumb-line audit skill and re-run. This report follows the principles you described, not that skill's exact rubric.