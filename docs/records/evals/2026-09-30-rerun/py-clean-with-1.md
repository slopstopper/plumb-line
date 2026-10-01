report-format: v4
scope:               fixture/ (whole tree)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the builder in the invocation): layers `ui -> services -> engine -> data`, one-way, non-adjacent downward skips allowed; priors from `config/`; `services` is the lineage-bearing output (source identity, record count, field names, config/version); outputs carry provenance and confidence and propagate the priors version. No source-truth layer was named, and none is inferred here, so checks under P1 — Source-truth layer are partial. What was checked and passed: every import points downward (`ui -> engine` is an allowed skip, `services -> engine`, `engine -> data`), and `.importlinter` encodes that direction (P2 — One-way layering). `signal_threshold` and `stub_confidence` are injected from `config/priors.toml` (P5 — Injectable priors). The stub records are labelled `data_status: "simulated"` and their confidence is capped (P4 — Quarantined fakery). The service output records all four lineage inputs (P8 — State-first lineage). `weights_version` propagates through engine, services and ui.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `fixture/src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | confidence is a fixed binary (1.0 when the mean clears the threshold, else 0.0), not derived from the data: a 3-record mean just above 0.65 reads as fully certain, and a null result ("no signal") gets confidence 0.0, which conflates "confidently no effect" with "no confidence" | derive confidence from the evidence (n, dispersion, margin to threshold) or document the 1.0/0.0 as a placeholder; give the null outcome its own confidence instead of zero | P3 — Confidence + provenance |
| `fixture/` | — | — | advisory | no source-truth layer is declared (layer direction is); `data/` holds only the schema, but nothing names which layer must stay free of derived or stub logic, so checks against it cannot be confirmed | name the source-truth layer in the project ruleset (for example `AGENTS.md`) | P1 — Source-truth layer |
| `fixture/src/` | — | — | advisory | adoption gap: no output shape has a versioned, validated contract (no validator, version constant or canonical key list); declared nowhere and practiced nowhere, so reported once | add a contract (version constant + key list + validator) for the service output first | P7 — Contracted outputs |
| `fixture/` | — | — | advisory | adoption gap: no tests and no golden baseline pin any output; declared nowhere and practiced nowhere, so reported once | pin the service output on the stub dataset as a golden baseline, with a drift-explanation rule | P9 — Golden baseline + explain-the-drift |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `fixture/src/engine/aggregate.py` `aggregate_records` | yes — derivation string, incl. field, n, threshold, config version | yes — but binary 1.0/0.0 (see needs-review row) | not required (engine is not the declared bearer); provenance string names n and config version | NO — adoption gap (P7 — Contracted outputs) | yes — `result: None`, `signal_detected: False`, empty-input paths | NO — adoption gap (P9 — Golden baseline + explain-the-drift) |
| `fixture/src/services/source.py` `load_and_aggregate` | yes — `stub source: ...` + `data_status: "simulated"` | yes — engine confidence capped by injected `stub_confidence` | yes — `lineage` dict: source, record_count, field_names, config_version (declared bearer, satisfied) | NO — adoption gap (P7 — Contracted outputs) | yes — passes through `result: None` / `signal_detected: False` | NO — adoption gap (P9 — Golden baseline + explain-the-drift) |
| `fixture/src/ui/report.py` `build_report` | yes — passed through from engine | yes — passed through from engine | not required (ui is not the declared bearer); priors version propagated as `weights_version` | NO — adoption gap (P7 — Contracted outputs) | yes — "No signal detected. Result: None" path | NO — adoption gap (P9 — Golden baseline + explain-the-drift) |

```
fixture/.importlinter                  read
fixture/.plumb-line/enforcement.json   read
fixture/config/priors.toml             read
fixture/src/__init__.py                read (empty)
fixture/src/data/__init__.py           read (empty)
fixture/src/data/schema.py             read
fixture/src/engine/__init__.py         read (empty)
fixture/src/engine/aggregate.py        read
fixture/src/services/__init__.py       read (empty)
fixture/src/services/source.py         read
fixture/src/ui/__init__.py             read (empty)
fixture/src/ui/report.py               read

coverage: 12/12 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only. Git history could not be
inspected (git is unavailable in this sandbox), so no baseline drift or
test-history evidence was checked. Whether .importlinter is actually run (CI or
a hook) was not verified; no CI or hook config is in scope.
```

format-validation: scripts/check_report_format.py v6 — clean

4 findings: 0 violations, 1 needs-review, 3 advisory

---

The fixture has no violations of the architecture you declared. The one item to decide on is the fixed 1.0 / 0.0 confidence in the engine; the other three are gaps in principles the project hasn't taken up yet. The format checker passed on the exact text above. Git isn't available in this sandbox, so history (for baseline drift or changes to tests) wasn't checked.

Next steps:
- **Save:** should I write this report to `plumb-line-audit.md`?
- **Fix:** I can run `plumb-line-remediate` on the findings. It shows you a diff for each one before changing anything.
- **Plan first:** or I can write a fix plan instead of making edits.