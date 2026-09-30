# Plumb-line audit: `./fixture`

**Note on method:** the plumb-line audit skill isn't installed in this session. It isn't in the available skills list and there's no `.claude/skills` directory, so I couldn't run it. I did the audit by hand against the architecture you declared. I read every source file, config file and enforcement file, and ran the project's own import-linter contract. The result may be less thorough than the skill's checklist, and the principle numbers (P2, P3) are my best reading of the fixture's own comments.

## Verdict: **PASS. No violations; 4 minor notes.**

---

## 1. Layer direction (ui → services → engine → data, downward skips allowed)

**Compliant.**

| Module | Imports | Direction |
|---|---|---|
| `src/ui/report.py:8` | `src.engine.aggregate` | ui → engine (downward skip, allowed) |
| `src/services/source.py:8` | `src.engine.aggregate` | services → engine (adjacent) |
| `src/engine/aggregate.py:7` | `src.data.schema` | engine → data (adjacent) |
| `src/data/schema.py` | none | bottom layer |

- There are no upward imports and no lateral imports between layers.
- The check is actually enforced: `.importlinter` defines a `layers` contract in the declared order, and `.plumb-line/enforcement.json` points to it.
- `lint-imports` ran on this fixture: **"plumb-line one-way layering KEPT. 1 kept, 0 broken"** (9 files, 3 dependencies).

## 2. Priors come from `config/`

**Compliant.**

- `config/priors.toml` holds `version`, `signal_threshold` and `stub_confidence`.
- The engine reads its threshold only from the `config` argument passed in (`aggregate.py:51`). There's no hardcoded threshold or weight.
- The services layer reads its trust cap from `config["stub_confidence"]` (`source.py:60`). It is not a literal in the code.
- The only numeric literals in `src/` are the stub records' values (data, not priors) and the confidence values 0.0 and 1.0 (see note B).

## 3. Services output carries lineage

**Compliant.** `load_and_aggregate` returns `lineage` (`source.py:45-50`) with all four required parts:

- **Source identity:** `"stub/_STUB_RECORDS"`
- **Record count:** `len(records)`
- **Field names:** `list(records[0].keys())`
- **Config/version:** `config["version"]`

It also returns `data_status: "simulated"`, which states honestly that the data is stubbed.

## 4. Provenance, confidence and priors version on every output

**Compliant.**

| Output | provenance | confidence | priors version |
|---|---|---|---|
| engine `aggregate_records` (all 3 return paths) | ✓ | ✓ | `weights_version` ✓ |
| services `load_and_aggregate` | ✓ (adds the `stub source:` prefix) | ✓ (`min(engine, stub_confidence)`: can only go down) | ✓ |
| ui `build_report` | ✓ passed through | ✓ passed through | ✓ as its own field *and* in `display_text` |

- Null results are handled explicitly. When no signal is found, `result: None` comes with provenance explaining why, rather than a guessed value.
- Uncertainty carries through correctly from engine to services.

---

## Minor notes (not violations)

**A. The lineage field list is sampled from the first record** (`source.py:48`). `records[0].keys()` misses fields if the records don't all share the same shape. `record_count` counts records, while the engine's provenance counts records that have a `value` field (`aggregate.py:39,60`), so the two can disagree. Neither matters for the uniform stub data, but both would under-report lineage with a real source. Suggestion: take the union of keys across all records, and optionally record how many records the engine actually used.

**B. Confidence is only ever 0.0 or 1.0** (`aggregate.py:64`). It reports whether a signal was detected, not how certain the mean is. A valid "no signal" result gets confidence 0.0, which reads as "don't trust this null" rather than "we're confident there's no signal." That weakens the confidence idea without breaking the rule. Consider deriving it from sample size or variance, or making it a prior in `config/`.

**C. Docstrings don't match the config actually used.**
- `source.py:29` and `report.py:18` describe `config` as containing only `version` and `signal_threshold`, but `source.py:60` also needs `stub_confidence`.
- `source.py:37` promises confidence "<1.0 when data is simulated". That only holds while `stub_confidence < 1.0` in `priors.toml`, and nothing enforces it.

**D. No code loads `config/priors.toml`, and the UI bypasses services.** Nothing in `src/` reads `priors.toml`; config is always passed in by a caller that isn't in the fixture. `ui/report.py` calls the engine directly with caller-supplied records, so the rendered report has no `lineage` or `data_status`. Both are allowed by what you declared: downward skips are permitted, and only the services layer has to carry lineage. But the report can't show whether its input was simulated. If the UI is meant to display service results, route it through `load_and_aggregate`, or pass `lineage` and `data_status` through.

---

**Summary:** the layer rule is enforced by tooling and currently holds. Priors come from `config/`. The services output has complete lineage. Every output carries provenance, confidence and the priors version. The notes above are about making these guarantees robust for real data sources, not about current breaches. I made no changes to the fixture.
