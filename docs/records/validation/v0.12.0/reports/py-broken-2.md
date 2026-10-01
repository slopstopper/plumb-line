report-format: v4
scope:               <harness>/fixtures/py-broken-2 (whole directory)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied in the invocation): layers ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors come from `config/`; the services output is the lineage bearer (source identity, record count, field names, config/version); outputs carry provenance and confidence and propagate the priors version. No source-truth layer was declared, so checks under P1 — Source-truth layer were not applied (see the advisory row and the coverage map).

Behavioural claims below were confirmed on a scratch copy under `work/py-broken-2/copy`, never in the target: importing any of `src.data.schema`, `src.engine.aggregate`, `src.ui.report`, `src.services.source` raises `ImportError` (circular import); `aggregate_records([{"value": 0.70}], {"signal_threshold": 0.9, ...})` returns `signal_detected: True` with `threshold=0.65` in its provenance.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/data/schema.py` | 7 | — (module import) | violation | data (bottom layer) imports `src.ui.report` (top layer), against the declared ui -> services -> engine -> data direction; it closes the cycle data -> ui -> engine -> data, so every module in `src/` fails to import. The shipped `.importlinter` layers contract would reject this import, so that gate is evidently not being run | remove the import; move `validate_and_display` into ui or a named composition root; run `lint-imports` in pre-commit/CI so the declared contract is enforced | P2 — One-way layering |
| `src/data/schema.py` | 24-26 | `validate_and_display` | violation | docstring claims "a quick validation pass", but no validation happens: `FIELD_TYPES` ("for validation") is never read anywhere, and the function only formats a ui report | implement validation against `FIELD_TYPES` (in a layer allowed to do it), or rename it and mark validation `not-implemented` | P6 — Maturity vocabulary |
| `src/engine/aggregate.py` | 9, 52 | `aggregate_records` | violation | the signal threshold is hardcoded (`SIGNAL_THRESHOLD = 0.65`), and the documented `config['signal_threshold']` (also in `config/priors.toml`) is ignored: config 0.9 still detects at 0.70. The output still stamps `weights_version` from config, so the recorded version does not describe the prior that was applied | read the threshold from the injected config and delete the module constant; add a test that changing the config threshold changes the verdict | P5 — Injectable priors |
| `src/engine/aggregate.py` | 65 | `aggregate_records` | violation | confidence just restates the verdict (`1.0 if signal_detected else 0.0`) and says nothing about the evidence: a single record just over the threshold is reported at confidence 1.0 | derive confidence from the evidence (record count, spread, margin to threshold), with its parameters in versioned config; or report it as unknown rather than certain | P3 — Confidence + provenance |
| `src/engine/aggregate.py` | 29-50, 54-65 | `aggregate_records` | needs-review | a measured no-effect (data present, mean below threshold) returns the same `signal_detected: False`, `result: None`, `confidence: 0.0` as "no records" / "no values"; inconclusive and no-effect differ only in free-text provenance, and `build_report` shows both as "No signal detected" | add an explicit outcome field (detected / not-detected / inconclusive) and give a measured null its own confidence instead of zero | spine — null-result expressibility |
| `src/services/source.py` | 37-45 | `load_and_aggregate` | violation | the declared lineage-bearing output records no lineage: no source identity (only the prose "stub source"), no structured record count, no field names; only `weights_version`. The count and field name appear only inside the free-text provenance string, which is not lineage | add a structured `lineage` field: source id, record count, field names used, config version and applied threshold | P8 — State-first lineage |
| `src/services/source.py` | 42 | `load_and_aggregate` | needs-review | the flat prior `config['stub_confidence']` replaces the engine's confidence instead of being combined with it, so upstream certainty is discarded (a no-data engine result at 0.0 would leave the service at 0.8) | combine the upstream confidence with the stub discount (for example min or product) and keep both visible | P3 — Confidence + provenance |
| `src/services/source.py` | 10-14, 34 | `load_and_aggregate` | needs-review | the only data path is hardcoded `_STUB_RECORDS`. It is labelled (`data_status: 'simulated'`, the `stub source:` prefix), but there is no opt-in: every caller gets simulated data carrying a signal verdict | gate the stub behind an explicit opt-in (for example `allow_simulated`), and otherwise fail or return inconclusive | P4 — Quarantined fakery |
| `src/services/source.py` | 1-33 | `load_and_aggregate` | needs-review | the module docstring calls this a "Fetch/persist boundary" that "loads raw records from a data source", and the return docs list `data_status` `'live'`, but there is no fetch, no persist and no live mode | mark the module `mock` in the maturity vocabulary and document `live` as `planned` | P6 — Maturity vocabulary |
| `src/ui/report.py` | 34-45 | `build_report` | violation | the declared rule "outputs propagate the priors version" is broken: the returned dict drops `weights_version`, which survives only inside the `display_text` string | add `weights_version` to the returned dict (and pass the service lineage through when the report is built from services) | P5 — Injectable priors |
| `src/` | — | — | advisory | no source-truth layer is declared (the layer direction is declared, but no layer is named for P1 — Source-truth layer), so the project's rules for ground truth exist only by convention | declare which layer holds measured/ground-truth data and what must never enter it | P6 — Maturity vocabulary |
| `src/` | — | — | advisory | adoption gap: P7 — Contracted outputs is neither declared nor practised; no output has a version constant, validator or canonical key list (only docstring key lists) | add a versioned, validated contract per public output, starting with the service output | P6 — Maturity vocabulary |
| `src/` | — | — | advisory | adoption gap: P9 — Golden baseline + explain-the-drift is neither declared nor practised; there is no baseline and no tests at all | pin the service output for the stub dataset in a golden baseline that requires a reason for any drift | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/engine/aggregate.py` `aggregate_records` | yes, a free-text string that names the threshold actually applied | PARTIAL: present, but it restates the verdict (1.0/0.0) | PARTIAL, not a declared bearer: `weights_version` is recorded, but the applied threshold is hardcoded, so the version does not reproduce it; count and field appear only in prose | NO (docstring keys only), adoption gap | PARTIAL: `result: None` and `signal_detected: False` exist, but inconclusive and no-effect are collapsed | NO, adoption gap |
| `src/services/source.py` `load_and_aggregate` | yes, the `stub source:` prefix on the engine string, plus `data_status` | PARTIAL: present, but the flat config prior replaces the engine's value | NO, declared bearer (P8 — State-first lineage): no source id, record count or field names; only `weights_version` | NO (docstring keys only), adoption gap | yes, `result: None` passed through (the collapse is inherited from the engine) | NO, adoption gap |
| `src/ui/report.py` `build_report` | yes, passed through from the engine | yes, passed through from the engine | NO: `weights_version` dropped from the returned dict (declared propagation) | NO (docstring keys only), adoption gap | PARTIAL: renders "No signal detected", but no-data is rendered the same way | NO, adoption gap |
| `src/data/schema.py` `validate_and_display` | yes, via `build_report` | yes, via `build_report` | NO: inherits the dropped `weights_version` | NO, adoption gap | PARTIAL, inherited from `build_report` | NO, adoption gap |

Coverage map:

| File | Status |
| ---- | ------ |
| `.importlinter` | read |
| `.plumb-line/enforcement.json` | read |
| `config/priors.toml` | read |
| `src/__init__.py` | read (empty) |
| `src/ui/__init__.py` | read (empty) |
| `src/ui/report.py` | read |
| `src/services/__init__.py` | read (empty) |
| `src/services/source.py` | read |
| `src/engine/__init__.py` | read (empty) |
| `src/engine/aggregate.py` | read |
| `src/data/__init__.py` | read (empty) |
| `src/data/schema.py` | read |

```
coverage: 12/12 files read, 0 partial, 0 not-read (100%)
scope note: findings are drawn from the read set only. No test files exist in scope, so check 10 (test changed to pass) had nothing to evaluate. No source-truth layer was declared, so coverage of P1 — Source-truth layer is partial; P2 — One-way layering was checked against the declared direction. Nothing in scope loads config/priors.toml; how callers inject it was not verifiable here. This audit does not claim completeness.
```

13 findings: 6 violations, 4 needs-review, 3 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

Notes below the report (not part of the checked text):

- **Checker:** I ran it on this exact text, saved as `<harness>/work/py-broken-2/checker-input.txt`. It had to be a `.txt` file because the host's Write tool refuses `.md` report files.
- **Target left unmodified:** the import and threshold probes (`work/py-broken-2/probe.py`) ran against a copy at `work/py-broken-2/copy`, with bytecode writing turned off. Nothing was written in the target.
- **No `plumb-line-audit.md` saved:** no builder was present to answer the save question.
- **No next step invoked:** also because no builder was present. The handoff that would normally be offered is `plumb-line-remediate` for the 6 violations. `plumb-line-bootstrap` would also apply, because the lineage (P8 — State-first lineage) and layering (P2 — One-way layering) gaps are real. The shipped `.importlinter` contract exists, but nothing runs it.

## Decisions needed

None. The audit was fully specified, and every judgement call was resolved inside the report (unsure items are marked `needs-review`).