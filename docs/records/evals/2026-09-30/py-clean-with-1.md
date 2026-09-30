report-format: v4
scope:               ./fixture (repository)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the owner in the invocation): layers ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors come from `config/`; services is the lineage-bearing layer (source identity, record count, field names, config/version); all outputs carry provenance and confidence and propagate the priors version. No source-truth layer was named explicitly, and the audit does not infer one. `src/data/` holds only static schema constants, so no derived or fake logic was found there, but P1 — Source-truth layer coverage is `partial`.

Layering check: `src/ui/report.py` -> `src/engine/aggregate.py` (a downward skip, allowed), `src/services/source.py` -> `src/engine/aggregate.py`, and `src/engine/aggregate.py` -> `src/data/schema.py`. No upward imports. `.importlinter` enforces this as a `layers` contract, and the import-linter cache agrees with the imports read here. P2 — One-way layering: clean.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | Confidence is hardcoded as a binary `1.0 if signal_detected else 0.0`. This is a judgment call (full certainty whenever the mean crosses the threshold, whatever the sample size; n=3 here) that is not in `config/priors.toml`. On the ui path, which skips services, `Confidence: 1.00` reaches the user with no `stub_confidence` cap | Derive confidence from the evidence (n, spread, distance from the threshold), or move the mapping into versioned priors in `config/` | P5 — Injectable priors |
| `src/engine/aggregate.py` | 28–49, 64 | `aggregate_records` | needs-review | "Inconclusive" (no records, or no values for the field) and "no effect" (mean below threshold) return the same structured output: `signal_detected=False`, `result=None`, `confidence=0.0`. Only the free-text `provenance` tells them apart, and `src/ui/report.py:30–33` shows all three as "No signal detected". A confident null and an absent measurement cannot be told apart, and a real no-effect result is reported with zero confidence | Add a structured outcome field (e.g. `detected` / `no_effect` / `inconclusive`) and give "no effect" its own confidence instead of reusing 0.0 | spine — null-result expressibility |
| `config/priors.toml` | — | — | advisory | No code in `src/` loads `config/priors.toml`. Every function accepts an arbitrary `config` dict, so nothing ties `weights_version` / `config_version` to the file's contents (the priors-from-`config/` rule depends on callers honoring it) | Add one composition-root loader that reads and validates `config/priors.toml` and passes it in | P5 — Injectable priors |
| `src/` | — | — | advisory | Adoption gap: no output shape has a versioned, validated contract (no validator, version constant, or canonical key list). Contracts are neither declared nor practiced anywhere in the fixture, so this is reported once, not per output | Declare contract constants and validators for the services and ui output shapes when this is adopted | P7 — Contracted outputs |
| `src/` | — | — | advisory | Adoption gap: there are no tests and no golden baselines, so no output value is pinned and drift cannot be detected or explained. This is neither declared nor practiced anywhere | Add a golden-baseline test over `load_and_aggregate` with the stub dataset and priors v1.0.0 | P9 — Golden baseline + explain-the-drift |

## Omission pass

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/engine/aggregate.py::aggregate_records` | YES — free-text derivation incl. n, threshold, config version | YES — but hardcoded binary 1.0/0.0 (needs-review, P5 — Injectable priors) | n/a — not the declared bearer; `weights_version` propagated | NO — adoption gap (P7 — Contracted outputs) | PARTIAL — `result=None` expresses null; inconclusive and no-effect share one structured form (needs-review) | NO — adoption gap |
| `src/services/source.py::load_and_aggregate` | YES — `stub source:` prefix plus engine derivation; `data_status: simulated` labels fakery (P4 — Quarantined fakery: clean) | YES — engine confidence capped by injected `stub_confidence` | YES — declared bearer: `lineage` has source, record_count, field_names, config_version | NO — adoption gap (P7 — Contracted outputs) | PARTIAL — inherits the engine's collapsed null/inconclusive form | NO — adoption gap |
| `src/ui/report.py::build_report` | YES — passed through from engine | YES — passed through from engine (uncapped, since the ui skips services) | n/a — not the declared bearer (downward skip allowed); `weights_version` propagated as a structured key | NO — adoption gap (P7 — Contracted outputs) | PARTIAL — "No signal detected" shown for both inconclusive and no-effect | NO — adoption gap |

## Coverage map

| File | Status |
| ---- | ------ |
| `src/__init__.py` | read (empty) |
| `src/ui/__init__.py` | read (empty) |
| `src/ui/report.py` | read |
| `src/services/__init__.py` | read (empty) |
| `src/services/source.py` | read |
| `src/engine/__init__.py` | read (empty) |
| `src/engine/aggregate.py` | read |
| `src/data/__init__.py` | read (empty) |
| `src/data/schema.py` | read |
| `config/priors.toml` | read |
| `.importlinter` | read |
| `.plumb-line/enforcement.json` | read |
| `.import_linter_cache/src.meta.json` | read (generated) |
| `.import_linter_cache/c3f7dc61d873e8291df9c567a548b9ed02a6dbab.data.json` | read (generated) |
| `.import_linter_cache/CACHEDIR.TAG` | not-read (generated tool marker) |
| `.import_linter_cache/.gitignore` | not-read (generated tool marker) |

```
coverage: 14/16 files read, 0 partial, 2 not-read (88%); all source, config and enforcement files read
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. P1 — Source-truth layer
coverage is partial because no source-truth layer was declared. The tree has no test files.
```

5 findings: 0 violations, 2 needs-review, 3 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

**Commit:** git couldn't run in the sandbox. Going by the session's git status, `fixture/` is untracked in a repo with no commits, so I recorded it as "working tree (uncommitted)".

**Result:** there are no confirmed violations. The fixture follows the architecture you declared: imports only go downward, the service output records full lineage, and the stub data is labelled.

**Next steps:** should I save this report to `plumb-line-audit.md`? After that I can hand the two needs-review findings to `plumb-line-remediate` to fix, or stop here.
