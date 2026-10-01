report-format: v4
scope:               fixture/ (repository sub-tree; declared architecture supplied by the project owner in the invocation)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P7 — Contracted outputs   P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (as supplied): layers `ui -> services -> engine -> data`, one-way, non-adjacent downward skips allowed (enforced by `.importlinter` layers contract); priors from `config/` (P5 — Injectable priors); `services` is the declared lineage bearer (P8 — State-first lineage: source identity, record count, field names, config/version); outputs carry provenance and confidence (P3 — Confidence + provenance) and propagate the priors version.

Presence-pass results: no upward imports (`ui -> engine` is an allowed downward skip; `services -> engine`, `engine -> data`); no hardcoded thresholds (`signal_threshold` and `stub_confidence` are injected from `config/priors.toml`); stub data in `src/services/source.py` is labelled (`data_status: "simulated"`, `"stub source: ..."` provenance, `stub/_STUB_RECORDS` lineage source) and its confidence is capped; the service output records all four declared lineage inputs; no tests exist, so no test-changed-to-pass finding is possible.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `fixture/src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | Confidence is the threshold decision re-encoded as 1.0 / 0.0, not a measure of certainty: a mean over 3 records just past the threshold reports full certainty, and a well-supported "no signal" reports zero confidence, so the null result looks untrustworthy rather than confident | Derive confidence from the evidence (record count, margin from threshold, spread) or inject the rule from `config/`; if the binary value is a deliberate placeholder, label it as such in the output | P3 — Confidence + provenance |
| `fixture/src/` | — | — | advisory | Adoption gap: no public output (engine, service or ui dict) has a versioned, validated contract (no schema version constant, canonical key list, or validator); this is neither declared nor practiced anywhere, so it is reported once | Add a contract version constant, a canonical key list and a validator for the service output first, since it is the declared lineage bearer | P7 — Contracted outputs |
| `fixture/` | — | — | advisory | Adoption gap: no tests and no golden baseline pin any output, so a drift in mean, signal decision or lineage would go unnoticed; neither declared nor practiced anywhere | Add a golden baseline for `load_and_aggregate` over the stub records and priors v1.0.0, with a recorded reason required for any change | P9 — Golden baseline + explain-the-drift |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `fixture/src/engine/aggregate.py` `aggregate_records` return dict | YES — derivation string with field, count, threshold, config version | PARTIAL — present but binary 1.0 / 0.0 (see needs-review) | N/A — engine is not the declared bearer; `weights_version` propagated | NO — docstring only (advisory, adopted nowhere) | YES — `result: None`, `signal_detected: False` on empty, missing-field and below-threshold paths | NO (advisory, adopted nowhere) |
| `fixture/src/services/source.py` `load_and_aggregate` return dict | YES — `stub source:` prefix plus engine derivation; `data_status: "simulated"` | YES — engine confidence capped by injected `stub_confidence` | YES — `lineage` records source, record_count, field_names, config_version (declared bearer satisfied) | NO — docstring only (advisory, adopted nowhere) | YES — passes through engine `None` / `False` | NO (advisory, adopted nowhere) |
| `fixture/src/ui/report.py` `build_report` return dict | YES — engine provenance passed through, structured and in display text | YES — engine confidence passed through | N/A — ui is not the declared bearer; `weights_version` propagated as a structured key | NO — docstring only (advisory, adopted nowhere) | YES — "No signal detected. Result: None" | NO (advisory, adopted nowhere) |

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
scope note: every in-scope file under fixture/ was read in full. Git history
could not be inspected (git unavailable in the sandbox), so the commit is
recorded as the working tree and no history-dependent check (baseline drift,
test changes) could draw on commits.
```

format-validation: scripts/check_report_format.py v6 — clean

3 findings: 0 violations, 1 needs-review, 2 advisory

---

The fixture has no confirmed violations. It follows the architecture you declared: layering, injected priors, the service lineage, labelled stub data, a null result every output can express, and the priors version passed through. The one thing to decide is whether the engine's all-or-nothing confidence (1.0 or 0.0) is intentional. The other two items are practices the project hasn't taken up yet: output contracts and golden baselines.

Should I save this report to `plumb-line-audit.md`? After that, I can start on the fixes with `plumb-line-remediate`, or write a fix plan first.