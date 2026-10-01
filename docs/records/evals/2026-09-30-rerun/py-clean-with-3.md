report-format: v4
scope:               fixture (repository)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P3 — Confidence + provenance   P5 — Injectable priors   P7 — Contracted outputs
P8 — State-first lineage       P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied in the invocation): ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors from `config/`; the services output is the lineage bearer (source identity, record count, field names, config/version); outputs carry provenance and confidence and propagate the priors version. The layering is machine-enforced by `.importlinter` (a `layers` contract, which permits downward skips). The imports checked match the declared direction: `ui -> engine`, `services -> engine`, `engine -> data`.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | Confidence is a binary restatement of the threshold decision (`1.0` if detected, else `0.0`), not a measure of certainty. A mean of 0.66 over 3 records against a 0.65 threshold reports full confidence, and a confident "no signal" reads as zero confidence. The `1.0`/`0.0` values are also unversioned judgment constants (P5 — Injectable priors). This flows through `src/services/source.py:60` and `src/ui/report.py:25,40,45`. | Derive confidence from the evidence (margin to threshold, record count), or make the rule an injected, versioned prior in `config/priors.toml`. Keep "confidence in the null" distinct from "no confidence". | P3 — Confidence + provenance |
| `src/engine/aggregate.py` | 28-49 | `aggregate_records` | needs-review | "No records" and "no values for the field" (inconclusive) return the same `signal_detected: False` / `result: None` shape as a measured "no signal". Only the free-text provenance tells them apart, and `src/ui/report.py:33` renders all three as "No signal detected". | Add a structured outcome field (e.g. `detected` / `not_detected` / `inconclusive`) and have the UI render inconclusive as such. | spine — null-result expressibility |
| `src/` | — | — | advisory | No output shape has a versioned, validated contract (no validator, version constant or canonical key list). This is declared nowhere and practised nowhere, so it is reported once as an adoption gap. | If adopted, add a schema version plus a key-list validator for the service and UI result dicts. | P7 — Contracted outputs |
| `src/` | — | — | advisory | No golden baseline (and no tests at all) pins any output, so drift in the mean, confidence or provenance would go unnoticed. This is declared nowhere and practised nowhere, so it is reported once as an adoption gap. | If adopted, pin `load_and_aggregate` against `config/priors.toml` v1.0.0 in a golden test and record the reason with each baseline change. | P9 — Golden baseline + explain-the-drift |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/engine/aggregate.py` `aggregate_records` | YES — derivation string with count, threshold and config version | PARTIAL — present but binary 1.0/0.0 (see findings) | N/A — not the declared bearer; `weights_version` is propagated | NO — docstring only (adoption gap) | PARTIAL — `None` result is expressible, but inconclusive is conflated with no-signal | NO (adoption gap) |
| `src/services/source.py` `load_and_aggregate` | YES — "stub source: ..." plus `data_status: simulated` | YES — engine confidence capped by injected `stub_confidence` | YES — `lineage` has source, record_count, field_names and config_version (declared bearer satisfied) | NO — docstring only (adoption gap) | PARTIAL — inherits the engine's null plus the inconclusive conflation | NO (adoption gap) |
| `src/ui/report.py` `build_report` | YES — passed through from the engine | YES — passed through (inherits the binary issue) | N/A — not the declared bearer; `weights_version` is propagated as a structured key | NO — docstring only (adoption gap) | PARTIAL — "No signal detected" is shown for the inconclusive case too | NO (adoption gap) |

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
```

coverage: 12/12 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only. Git history could not be inspected (git is unavailable in the sandbox), so baseline and test changes over time were not assessed. This audit does not claim completeness.

4 findings: 0 violations, 2 needs-review, 2 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

The audit found no confirmed violations. The layering, priors, lineage and stub labelling all match the declared architecture. The two `needs-review` items are about whether confidence and null results are reported honestly. The two advisories are principles the project hasn't taken up yet. I didn't change any files.

Should I save this report to `plumb-line-audit.md`? After that, I can hand the two `needs-review` findings to `plumb-line-remediate` to fix, or to a planning step if you'd rather plan the changes first.