report-format: v4
scope:               <harness>/fixtures/py-clean (repository)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P3 — Confidence + provenance  P4 — Quarantined fakery
P5 — Injectable priors       P6 — Maturity vocabulary      P7 — Contracted outputs
P8 — State-first lineage     P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the owner in the invocation): the layers run one way, ui -> services -> engine -> data, and a layer may skip a non-adjacent layer below it. Priors come from `config/`. The services layer is the lineage-bearing output: its result records source identity, record count, field names and config version. All outputs carry provenance and confidence, and pass the priors version on. The declaration does not say which layer is the source-truth layer (P1 — Source-truth layer), and the scope holds no `AGENTS.md` or `CLAUDE.md` that could. The audit does not infer one, so the P1 — Source-truth layer check is `partial` (see the coverage map).

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | `confidence` is `signal_detected` restated as a hardcoded 1.0 or 0.0, not derived from record count, spread or distance from the threshold. A mean of 0.6501 over 3 records against a threshold of 0.65 reports certainty 1.0. A measured no-signal result reports 0.0, the same as the no-data case (lines 34, 47). The services cap at `src/services/source.py:60` therefore inherits values that measure nothing. Unlike the sibling `stub_confidence`, these confidence levels are not in `config/priors.toml` (P5 — Injectable priors). | Derive confidence from the evidence (n, spread, margin to threshold), or lift the levels to versioned config. State what the confidence is confidence *in*, so that a confident "no signal" is different from "unknown". | P3 — Confidence + provenance |
| `src/ui/report.py` | 30-33, 43 | `build_report` | needs-review | With zero records, the summary line says "No signal detected. Result: None", which reports an inconclusive run as a no-effect result. The returned dict drops `mean` and `result`. That leaves no-data and measured-no-signal with the same `signal_detected: False` and `confidence: 0.0`, and a consumer can tell them apart only by parsing the free-text `provenance`. The engine keeps the distinction (`mean` is None only for no-data). | Pass through an explicit outcome (detected / not-detected / inconclusive) or `mean`, and render the no-data case as inconclusive rather than "No signal detected". | spine — null-result expressibility |
| `src/services/source.py` | 1-6, 10-15, 37-38 | `load_and_aggregate` | advisory | This is `mock`-maturity code: its only source is the module-private `_STUB_RECORDS`. Yet the module docstring calls it a "Fetch/persist boundary" that "loads raw records from a data source" (nothing is fetched or persisted), and it documents a `'live'` `data_status` that no code path produces. The maturity vocabulary is used nowhere in the project, so this is reported once. Runtime labelling is present and good (`data_status: simulated`, a "stub source:" provenance, `lineage.source`). There is no opt-in gate, which will matter once a live path exists (P4 — Quarantined fakery). | Mark the module `mock` in the maturity vocabulary and describe its current behaviour. When a live path lands, require an explicit opt-in before stub data is returned. | P6 — Maturity vocabulary |
| `src/` | — | — | advisory | Adoption gap, reported once as a maturity note (P6 — Maturity vocabulary). None of the three outputs has a versioned, validated contract: no version constant, validator or canonical key list, only key lists in docstrings. Neither the declaration nor any sibling code adopts contracts. `src/data/schema.py:7-8` declares `FIELD_TYPES` "for validation", but nothing validates against it. | Give each public output shape a version constant, a validator and a key-list constant, starting with the services output. | P7 — Contracted outputs |
| `src/` | — | — | advisory | Adoption gap, reported once as a maturity note (P6 — Maturity vocabulary). No derived output is pinned in a golden baseline (the scope has no baseline files and no tests), so a change to `signal_threshold` or to the aggregation would shift results with nothing to show it. Neither the declaration nor any code adopts baselines. | Pin the services output for the stub dataset under config v1.0.0, and require a written reason whenever the pinned values change. | P9 — Golden baseline + explain-the-drift |
| `—` | — | — | advisory | Architecture gap. The supplied declaration gives layers and direction but no source-truth layer (P1 — Source-truth layer), and the scope has no ruleset file. The audit does not infer one, so that check is partial. Under any reading, `src/data/schema.py` holds only static type maps, with no derived, synthesized or fake logic, and the stub records live in `src/services/`, not `src/data/`. | Declare the source-truth layer (likely `src/data`, if that is what the owner means) in a ruleset file, so future audits can check it fully. | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `aggregate_records` (`src/engine/aggregate.py`) | YES: free-text string naming the field, n, threshold and config version | PRESENT but uninformative: 1.0 or 0.0 mirrors `signal_detected` (finding, P3 — Confidence + provenance) | NOT REQUIRED: not a declared bearer. n and config version appear only inside the provenance string; no source identity or field list. `weights_version` present | NO: docstring key list only (adoption gap) | YES: `result` None or `signal_detected` False; no-data told apart by `mean` None | NO (adoption gap) |
| `load_and_aggregate` (`src/services/source.py`) | YES: "stub source:" prefix plus the engine string, and `data_status: simulated` | YES: `min(engine, config stub_confidence)`; inherits the engine concern | YES, declared bearer (P8 — State-first lineage): `source`, `record_count`, `field_names`, `config_version`; `weights_version` also propagated | NO: docstring key list only (adoption gap) | YES: `result` and `mean` pass through as None | NO (adoption gap) |
| `build_report` (`src/ui/report.py`) | YES: passed through from the engine | YES: passed through from the engine | NOT REQUIRED: not a declared bearer; none recorded. `weights_version` propagated | NO: docstring key list only (adoption gap) | PARTIAL: no-signal can be expressed, but inconclusive (no records) collapses into "No signal detected" (finding, spine — null-result expressibility) | NO (adoption gap) |

Coverage map:

```
read      .importlinter
read      .plumb-line/enforcement.json
read      config/priors.toml
read      src/__init__.py            (empty)
read      src/data/__init__.py       (empty)
read      src/data/schema.py
read      src/engine/__init__.py     (empty)
read      src/engine/aggregate.py
read      src/services/__init__.py   (empty)
read      src/services/source.py
read      src/ui/__init__.py         (empty)
read      src/ui/report.py
coverage: 12/12 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only. Imports were checked by
reading: engine->data, services->engine and ui->engine (a declared skip) all
follow the declared direction, and .importlinter encodes that layer order. The
import-linter contract was not executed. No entry point in scope loads
config/priors.toml, so "priors come from config/" is confirmed only in that
every prior is read from an injected dict whose keys match that file. There
are no tests in scope, so check 10 (test changed to pass) had nothing to
examine. The P1 — Source-truth layer check is partial because no source-truth
layer is declared. This audit does not claim completeness.
```

6 findings: 0 violations, 2 needs-review, 4 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

(Below the report.) I ran the checker on the exact text above, and it is also saved at <harness>/work/py-clean/plumb-line-audit.md (the harness work directory; I did not write `plumb-line-audit.md` into the target, as the skill requires). The target directory was not modified. Nobody was available to answer questions, so I made no handoff offer and invoked no skill that edits files.

The audit found no violations. The declared lineage for the services layer is present and complete, and every import follows the declared layer direction. The two needs-review items are:
- The engine's confidence value is just the signal flag restated as 1.0 or 0.0, so it measures nothing.
- The ui reports "no records" as "No signal detected", making an inconclusive run look like a no-effect result.

## Decisions needed
1. Which layer is the source-truth layer? Recommendation: declare `src/data` in a ruleset file (it holds only static type maps today), so the next audit can check it fully instead of partially.
2. Should the two needs-review items (the 1.0/0.0 confidence in the engine, and the ui showing "no records" as "No signal detected") be confirmed as intended fixture behaviour or treated as real defects? Recommendation: treat them as real. The spine principle says an inconclusive result must never collapse into "no effect", and a confidence that just repeats the signal flag tells a consumer nothing.