# Plumb-line audit: `./fixture`

**About the method:** I couldn't find a plumb-line audit skill. It isn't among the skills available in this session, and `.claude/` holds no skill files. So I did the audit by hand against the architecture you declared. I checked it two ways: I ran the project's own enforcement (`lint-imports`, configured by `.plumb-line/enforcement.json`), and I ran the pipeline on `config/priors.toml` to look at real outputs.

## Verdict: **No violations. There are 3 advisory findings, one of them important.**

## Architecture as declared

| Item | Declared |
|---|---|
| Layers | `ui → services → engine → data`, one-way; downward skips over a layer are allowed |
| Priors | come from `config/` |
| Lineage-bearing output | the services layer (records source, record count, field names, config version) |
| Every output | carries provenance and confidence, and passes on the priors version |

## Checks

### 1. Layer direction: PASS
| Import | Direction | Status |
|---|---|---|
| `src/engine/aggregate.py:7` → `src.data.schema` | engine → data | ✅ |
| `src/services/source.py:8` → `src.engine.aggregate` | services → engine | ✅ |
| `src/ui/report.py:8` → `src.engine.aggregate` | ui → engine, skipping services | ✅ allowed skip |
| `src/data/schema.py` | no imports | ✅ |

`lint-imports`: **"plumb-line one-way layering KEPT — 1 kept, 0 broken"** (9 files, 3 dependencies). Nothing imports upward. The `.importlinter` layers contract matches the declared order.

### 2. Priors from `config/`: PASS
- `signal_threshold` is read only from the config passed in (`aggregate.py:51`). No threshold is written into the code.
- `stub_confidence` is read from config (`source.py:60`). It isn't a magic number.
- `version` goes into every output as `weights_version`.
- None of the layers loads config itself. The caller passes it in, which is clean.

### 3. Lineage on the services output: PASS
`load_and_aggregate` returned:
```
lineage: {source: 'stub/_STUB_RECORDS', record_count: 3,
          field_names: ['id','value','category','timestamp'], config_version: '1.0.0'}
```
All four required parts are there (`source.py:45-50`). The output is also marked `data_status: 'simulated'`.

### 4. Provenance, confidence and priors version on every output: PASS
| Output | provenance | confidence | weights_version |
|---|---|---|---|
| engine `aggregate_records` (all 3 return paths) | ✅ | ✅ | ✅ |
| services `load_and_aggregate` | ✅ (prefixed with "stub source:") | ✅ (capped) | ✅ |
| ui `build_report` | ✅ | ✅ | ✅ as its own key (`report.py:48`) and in the display text |

Empty and "no signal" results come back as `result: None` with a reason in provenance. The code doesn't make up a value when it has none.

## Advisory findings

**A1: The UI skips services and loses the simulated-data confidence cap (important).**
`build_report` calls the engine directly on raw records, which the declared skip rule allows. The trouble is that it bypasses the one place that caps confidence for stub data and labels the data as simulated. On the same stub records and config:
- the services output shows `confidence: 0.8, data_status: 'simulated'`, plus lineage
- the UI output shows `Confidence: 1.00`, with no `data_status` and no lineage

So the report users see claims more certainty than the lineage-bearing layer does, and it doesn't say the data is simulated. That runs against "uncertainty propagates, not discarded", even though the import itself is legal. **Fix:** have the UI render the services result, e.g. `build_report(service_result)`, so it passes on `confidence`, `data_status` and `lineage`. Or have the caller pass those fields in.

**A2: Engine confidence is just on or off, set in code (`aggregate.py:64`).**
The engine sets `confidence` to `1.0 if signal_detected else 0.0`. That's the yes/no decision restated, not a measure of how sure it is. A mean of 0.651, just over the 0.65 threshold, gets full confidence. The docstring says "float 0–1", which suggests a graded value. **Fix:** calculate confidence from distance to the threshold and sample size, with any scaling setting coming from `priors.toml`. Or document that it's only an on/off indicator.

**A3: Minor fidelity gaps in lineage and docs.**
- `field_names` comes only from `records[0]` (`source.py:48`), so mixed-schema inputs would be under-reported. `record_count` counts every record, while the engine only averages records that have a `value` field. The two counts can differ, and lineage wouldn't show it.
- Lineage stores `config_version` but not the prior values actually used (`signal_threshold`, `stub_confidence`). Reproducing a result therefore depends on the versioned `priors.toml` staying unchanged.
- The `load_and_aggregate` docstring (`source.py:29`) lists config as `version` + `signal_threshold`, but the code also needs `stub_confidence`.
- The `report.py` docstring says "Allowed imports: engine only". That's stricter than the declared rule, which is fine but differs from it.

## Summary
| Check | Result |
|---|---|
| One-way layering (enforced, `lint-imports` KEPT) | ✅ |
| Priors from config | ✅ |
| Services lineage (source, count, fields, config version) | ✅ |
| Provenance, confidence, priors version on all outputs | ✅ |
| Advisories | A1 (important), A2, A3 (minor) |

No files were changed.
