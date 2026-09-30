# Plumb-line audit: `./fixture`

**About the method:** no plumb-line audit skill is installed in this session. The only skills available are dataviz, code-review, simplify, security-review and a few others, and there's no `.claude/skills` in the repo. So I did this audit by hand against the architecture you declared, using the principle numbers referenced in the fixture's own comments (P2 layering, P3 uncertainty). The finding format and severity labels are mine, not the skill's. If you install the skill, re-run it to get the canonical report.

**How I checked:**
- Read all 12 source and config files.
- Ran `lint-imports --no-cache` against `.importlinter`.
- Called the pipeline with `config/priors.toml` and with a few edge-case inputs.
- Deleted the `__pycache__` directories my test run created. Nothing else was modified.

## Summary

| Area | Verdict |
|---|---|
| One-way layering (ui → services → engine → data, skips allowed) | **Pass**, with a note (F-3) |
| Priors come from `config/` | **Partial.** Values are injected, but nothing in the code loads `config/`, and one hardcoded value affects confidence (F-1) |
| Service lineage (source, record count, field names, config version) | **Pass**, with gaps that affect reproduction (F-2, F-4) |
| Provenance and confidence on outputs | **Present in every output**, but the confidence value overstates certainty (F-1) |
| Priors version propagated | **Pass** (engine → services → ui) |

## Verified passes

- **Layering.** `lint-imports` reports "plumb-line one-way layering KEPT, 1 kept, 0 broken". There are three import edges:
  - `engine.aggregate → data.schema` (`src/engine/aggregate.py:7`)
  - `services.source → engine.aggregate` (`src/services/source.py:8`)
  - `ui.report → engine.aggregate` (`src/ui/report.py:8`), which is an allowed downward skip.
  
  No module imports a higher layer. The contract's layer order matches the declared architecture, and `.plumb-line/enforcement.json` points to it.
- **Priors are injected, not hardcoded in the engine.** `signal_threshold` (`aggregate.py:51`) and `stub_confidence` (`source.py:60`) both come from the `config` argument, and `config/priors.toml` defines both along with `version = "1.0.0"`.
- **Service lineage has all four required fields** (`source.py:45-50`). The run returned `{'source': 'stub/_STUB_RECORDS', 'record_count': 3, 'field_names': ['id','value','category','timestamp'], 'config_version': '1.0.0'}`.
- **Version propagation.** `weights_version` is returned by the engine on all three return paths, passed through by services (`source.py:63`), and exposed by the UI as a structured key (`report.py:48`), not only in the display text.
- **Null result is explicit.** When no signal is detected, `result` is `None`, and provenance says why.
- **Simulated data is marked.** Services returns `data_status: "simulated"` and caps confidence at `stub_confidence`. The cap can only lower confidence, never raise it (`source.py:57-60`).

## Findings

### F-1 — High — Confidence is a hardcoded 0/1 value, not a measure of uncertainty (P3)
`src/engine/aggregate.py:64`: `"confidence": 1.0 if signal_detected else 0.0`
- Confidence just repeats the threshold decision, so it adds no information. It jumps from 0.0 to 1.0 when the mean crosses 0.65, however close it is and however few records there are. It also ignores how many records were dropped (see F-2).
- Reproduced: `build_report([{'id':'x','value':0.66},{'id':'y'}], cfg)` returns **Confidence: 1.00** from one usable value out of two records, 0.01 above the threshold.
- 0.0 means two different things: "confident there is no signal" and "no data at all" (`aggregate.py:34`, `:47`).
- The `1.0` and `0.0` values are fixed in the code, not priors from `config/`.
- Services hides this for stub data because of the `min(…, 0.8)` cap. The UI path (F-3) has no cap and shows the raw 1.00.
- **Fix:** compute confidence from sample size and distance to the threshold, with any constants taken from `priors.toml`. Keep "no data" separate from "confident negative", for example by returning `confidence: None` when there is nothing to measure.

### F-2 — Medium — Records missing the field are silently dropped, so lineage can disagree with the computation
`src/engine/aggregate.py:39`: `values = [r[field] for r in records if field in r]`
- Records without the `value` field are skipped without any record of it. Provenance reports `len(values)`, but the service lineage reports `record_count = len(records)` (`source.py:47`). If any records are skipped, the two counts disagree, and the lineage doesn't show which field was aggregated or how many records were excluded.
- The current stub data doesn't hit this, but real input would. I reproduced it on the UI path: two records in, and provenance says "over 1 records".
- **Fix:** have the engine return `used_count`, `dropped_count` and `aggregated_field`, and have services add them to the lineage.

### F-3 — Medium — The UI output has no lineage or `data_status`
`src/ui/report.py:8,28`: the UI calls `engine.aggregate_records` directly with caller-supplied records and never goes through the service layer, which is the one that produces lineage.
- The import is allowed as a downward skip, and `lint-imports` accepts it. But the report users actually see has no lineage, no `data_status`, and no confidence cap. The declared lineage guarantee therefore stops before the presentation layer.
- The docstring also contradicts itself. It says "Does not calculate — delegates entirely to the engine", but the UI is the component that runs the computation. It also says "formats engine output", yet the lineage-bearing output it is supposed to present comes from services.
- **Fix:** have `build_report` take the result dict from `load_and_aggregate` and format it, passing `lineage` and `data_status` through. Or, if the direct engine path is intentional, say so in the architecture statement.

### F-4 — Low — Lineage identifies the source but can't guarantee it's reproduced exactly
`src/services/source.py:46,48`
- `source: "stub/_STUB_RECORDS"` is a name only. It has no content hash or version, so if the dataset changes, the recorded lineage still looks the same.
- `field_names` is taken from `records[0]` only, so if later records have different fields, the lineage under-reports them.
- **Fix:** add a content digest, such as a SHA-256 of the canonicalised records, and take the union of keys across all records.

### F-5 — Low — Nothing in the code loads the priors from `config/`
Nothing in `src/` reads `config/priors.toml`; a grep for `priors` and `toml` found only comments. The config is always passed in by the caller, so the code alone can't show that the priors come from `config/` and not from a hand-built dict with the same keys.
- **Fix:** add a small loader outside the layered packages, or a startup entry point, that reads `config/priors.toml` and checks it has `version`, `signal_threshold` and `stub_confidence`.

### F-6 — Low — Documentation drift and naming inconsistencies
- `source.py:29` documents `config` as containing `version` and `signal_threshold`, but the code also needs `stub_confidence`, and a `KeyError` is raised if it's missing.
- `report.py:4-5` says the UI may import "engine only". The declared architecture also allows ui → services, and fixing F-3 needs that.
- The same value is called `weights_version` in outputs and `config_version` in lineage. One name would make the chain easier to follow.
- `FIELD_TYPES` in `data/schema.py:8` is defined but never used to validate records, so a non-numeric `value` would fail inside `sum()` with an unclear error.

## Findings by severity

| Severity | Count | IDs |
|---|---|---|
| High | 1 | F-1 |
| Medium | 2 | F-2, F-3 |
| Low | 3 | F-4, F-5, F-6 |

The one-way layering is met and enforced, and version propagation is met. The problems are in how honest the confidence value is (F-1) and in lineage not being complete end to end (F-2, F-3).
