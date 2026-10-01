# Plumb-line audit: `./fixture`

**Before the findings:** there is no plumb-line audit skill in this session. It isn't in the available skills list, and there's nothing under `.claude/skills` in the workspace. So I did this audit by hand against the architecture you declared, and it doesn't follow the skill's official checklist or scoring. If you install the skill and rerun, its output may be structured differently.

**How I checked it:**
- Read all 12 files.
- Ran `lint-imports`.
- Ran the pipeline with `config/priors.toml`, with a record below the threshold, and with a changed threshold.
- Deleted the `__pycache__` folders my test runs created. Nothing else in the fixture was changed.

## Summary

| Area | Result |
|---|---|
| One-way layering (ui → services → engine → data) | ✅ Pass. `lint-imports`: 1 contract kept, 0 broken. |
| Priors come from config/ | ⚠️ Partial. No hardcoded thresholds, but no code actually reads `config/`. |
| Service layer records lineage | ✅ Pass, with two minor accuracy gaps. |
| Outputs carry provenance and confidence | ⚠️ Present, but the confidence value is misleading (F1). |
| Priors version is passed through | ✅ Pass (engine → services and engine → ui). |

## Findings

**F1: Confidence is really just "was a signal detected" (medium)**
- **Where:** `src/engine/aggregate.py:64`
- **What:** `"confidence": 1.0 if signal_detected else 0.0`. This doesn't measure uncertainty; it repeats `signal_detected`.
  - A mean of 0.7033 against a threshold of 0.65 gets full certainty (1.0), even though it's based on only 3 records.
  - A clear "no signal" result gets 0.0, which reads as "we know nothing" rather than "confidently negative".
  - The empty-input and missing-field cases at lines 34 and 47 also return 0.0. That makes them look the same as a real negative result.
- **Knock-on effect:** `services/source.py:60` caps confidence with `min(engine, stub_confidence)`. Lowering a value is fine, but any negative result stays at 0.0 whatever the cap is. With a threshold of 0.9 the service returned `confidence: 0.0` for data it had fully measured.
- **Fix:** base confidence on sample size and how far the mean is from the threshold, and keep "no data" separate from "negative result".

**F2: No code loads priors from `config/` (medium)**
- **Where:** `config/priors.toml` is never read. Neither is `stub_confidence`, which `source.py:60` uses as a prior.
- **What:** the engine and service take whatever `config` dict the caller passes in. Nothing enforces that it came from `config/priors.toml`, or checks that the keys `version`, `signal_threshold` and `stub_confidence` exist and have the right types. A caller can build a dict inline, and the output will still claim to use that config version.
- **Fix:** add one loader (e.g. `load_priors()` reading `config/priors.toml`) that entry points must use, and validate the keys there.

**F3: The config version is only a label (low)**
- **Where:** `source.py:49` and `aggregate.py:35/48/65`
- **What:** `config_version` / `weights_version` just echo `config["version"]`. I changed `signal_threshold` from 0.65 to 0.9 and every output still said version `1.0.0`. So lineage alone can't reproduce the result.
- **Fix:** record a hash of the config content alongside the version, or put the values that were actually used (e.g. `threshold`) into `lineage`.

**F4: Record count in lineage can differ from what was aggregated (low)**
- **Where:** `aggregate.py:39` versus `source.py:47-48`
- **What:**
  - The engine quietly skips records that lack the `value` field, but the lineage reports `record_count = len(records)`.
  - `field_names` is taken from `records[0]` only, so the lineage is wrong if records have different fields.
- **Fix:** record both the loaded count and the used count, and take `field_names` from all records combined.

**F5: The schema's types are declared but never checked (low)**
- **Where:** `src/data/schema.py:8-19`
- **What:** nothing uses `FIELD_TYPES` or `IDENTIFIER_FIELDS`. A string in `value` would only fail later, inside `sum()`, rather than when the data comes in.

## Notes (not violations)

- **The UI skips the services layer:** `ui/report.py:8` imports the engine directly. You allowed downward skips, and the import linter is happy with it. The side effect is that the report users see has provenance, confidence and version, but no `lineage` and no `data_status`. If the report should be reproducible too, have it go through `services.load_and_aggregate`.
- **Import checking is in place:** `.importlinter` and `.plumb-line/enforcement.json` are set up, and the layering contract passes.
- **Stub data is honestly labelled:** `data_status: "simulated"` and the `stub source:` provenance prefix are good practice.
- **No tests:** the fixture has none, so none of the points above are covered.

## Verdict

The structure is sound: the layer direction holds and lineage, provenance and version all flow through. The weak spots are how honest the confidence number is (F1) and whether priors really come from `config/` (F2). Fix those two first. F3 and F4 are small changes to make lineage accurate.