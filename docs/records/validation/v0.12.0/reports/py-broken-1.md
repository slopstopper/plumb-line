report-format: v4
scope:               <harness>/fixtures/py-broken-1 (repository)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the project owner in the invocation): layers ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors come from `config/`; the services layer is the lineage-bearing output (source identity, record count, field names, config/version); all outputs carry provenance and confidence and propagate the priors version. `.importlinter` declares the same four layers in the same order. No source-truth layer is named in the declaration or in any ruleset in the tree, so the audit does not infer one: coverage of P1 — Source-truth layer is `partial` (see the advisory row and the coverage map). P2 — One-way layering is fully checkable against the declared direction.

Traversal plan (the denominator): 12 files — 7 non-empty (`.importlinter`, `.plumb-line/enforcement.json`, `config/priors.toml`, `src/data/schema.py`, `src/engine/aggregate.py`, `src/services/source.py`, `src/ui/report.py`) and 5 empty `__init__.py` files. All 12 to be read; none sampled or skipped. There are no test files in the tree. To confirm the boundary finding, the source was copied to a scratch directory and each module imported there (the target was not modified).

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/data/schema.py` | 7, 24-26 | `validate_and_display` (module import) | violation | Bottom layer (data) imports and calls the top layer (`from src.ui.report import build_report`), against the declared ui -> services -> engine -> data direction and the `.importlinter` layers contract. It closes the cycle ui -> engine -> data -> ui: importing a copy of the tree shows every module (`src.ui.report`, `src.services.source`, `src.engine.aggregate`, `src.data.schema`) fails with a circular-import `ImportError`, so no entry point loads. The configured boundary contract did not stop this. | Remove the import and move `validate_and_display` to the ui layer (or a named composition root); run the `.importlinter` contract as a blocking gate | P2 — One-way layering |
| `src/engine/aggregate.py` | 9, 52 | `aggregate_records` | violation | Signal threshold hardcoded as `SIGNAL_THRESHOLD = 0.65`. The docstring says it comes from `config['signal_threshold']` and `config/priors.toml` supplies it, but the config value is never read. The output still stamps `weights_version = config['version']`, so it credits a config version with a threshold that config did not provide. Changing the prior in config would change nothing, yet the version would change. | Read the threshold from the injected config (fail if it is missing) and delete the module constant | P5 — Injectable priors |
| `src/engine/aggregate.py` | 65 | `aggregate_records` | violation | `confidence` is `1.0 if signal_detected else 0.0`: a restatement of the decision, not a measure of certainty. It is 1.0 for a mean of 0.651 over 3 records and 0.0 for 0.649. A confident "no signal" reads the same as "no confidence". The 1.0/0.0 values are also unversioned judgment constants. | Derive confidence from the evidence (sample size, margin to threshold) using injected, versioned parameters, or report it as not computed rather than inventing it | P3 — Confidence + provenance |
| `src/services/source.py` | 42 | `load_and_aggregate` | violation | The engine's `confidence` is dropped (`aggregated['confidence']` is never read) and replaced by the flat prior `config['stub_confidence']` (0.8), whatever the result. When the engine reports 0.0, the service still reports 0.8. `stub_confidence` is also missing from the docstring's config key list (line 22). | Combine the stub prior with the engine's confidence (for example, take the weaker) and record both, rather than overwriting one with the other | P3 — Confidence + provenance |
| `src/services/source.py` | 37-45 | `load_and_aggregate` | violation | The declared lineage-bearing output records no reproduction inputs as structured fields. There is no source identity, record count or field names, and neither the threshold nor `stub_confidence` value that was used is recorded. Only `weights_version` is present. Record count and field name appear only inside the free-text `provenance` string, and a provenance string does not satisfy lineage. | Add a structured `lineage` field (source id, record count/ids, fields used, priors version and the prior values actually applied) and assert it in a test | P8 — State-first lineage |
| `src/services/source.py` | 1-5, 17-33 | `load_and_aggregate` (module docstring) | violation | The docstrings describe a "Fetch/persist boundary" that "loads raw records from a data source" and a `data_status` of `'simulated' \| 'live'`. The only path is the hardcoded `_STUB_RECORDS`: nothing is fetched or persisted, and `'live'` cannot be returned. The line 9 comment and the `simulated` label are honest; the public docstrings are not. | State the maturity plainly: the loader is `mock` and `live` is `planned`. Remove `'live'` from the documented return until a real path exists | P6 — Maturity vocabulary |
| `src/services/source.py` | 10-14, 34 | `load_and_aggregate` | needs-review | Stub records always flow into the service output. They are labelled (`data_status: 'simulated'`, "stub source" provenance prefix), but there is no opt-in gate and no real alternative path. The repo does not establish whether the owner treats the service result as an output path that must exclude simulated data unless opted in. | Require an explicit opt-in (for example, an `allow_simulated` parameter) before stub-derived results are returned | P4 — Quarantined fakery |
| `src/data/schema.py` | 24-26 | `validate_and_display` | violation | The docstring promises "a quick validation pass", but the function validates nothing: it only forwards to `build_report`. `FIELD_TYPES`, documented as existing "for validation", is referenced nowhere in the code. | Implement validation against `FIELD_TYPES` (in a layer allowed to hold it), or rename the function and correct its docstring | P6 — Maturity vocabulary |
| `src/ui/report.py` | 34-45 | `build_report` | needs-review | The declaration says outputs propagate the priors version, but the structured return omits `weights_version`. It survives only as text inside `display_text` ("Config version: ..."), so a programmatic consumer loses it. | Add `weights_version` (passed through from the engine) as a key of the returned dict | P5 — Injectable priors |
| `src/engine/aggregate.py` | 29-37, 42-50, 54-59 | `aggregate_records` | needs-review | "Inconclusive" (no records or no values) and "no effect" (measured, below threshold) produce identical structured fields: `signal_detected: False`, `result: None`, `confidence: 0.0`. Only the free-text `provenance` differs. `build_report` renders both as "No signal detected", so no data reads as a negative finding. | Add an explicit outcome field (for example, `detected` / `not-detected` / `inconclusive`) and render inconclusive distinctly | spine — null-result expressibility |
| `src/` | — | — | advisory | Adoption gap: no output shape has a versioned, validated contract (no version constant, validator or canonical key list). Key lists exist only in docstrings. It is neither declared nor practiced anywhere, so it is reported once rather than per output. | Give the service output (the declared lineage bearer) a version constant, key list and validator first | P7 — Contracted outputs |
| `src/` | — | — | advisory | Adoption gap: no golden baseline pins any derived output (there are no tests or fixtures at all). It is neither declared nor practiced, so it is reported once. | Pin `load_and_aggregate` output for the stub dataset under a named priors version, and require a recorded reason when it changes | P9 — Golden baseline + explain-the-drift |
| `.importlinter` | 5-12 | — | advisory | The architecture declares a layer order but names no source-truth layer, here or in the owner's declaration. P1 — Source-truth layer checks (derived or mock logic inside the ground-truth layer) therefore cannot be applied, and that principle's coverage is partial. | Name the source-truth layer (for example, via `plumb-line-bootstrap` declaration-only entry) and what must never enter it | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/services/source.py` `load_and_aggregate` | partial: free-text string with "stub source" prefix, plus `data_status: 'simulated'` | substituted: flat `stub_confidence` prior replaces the engine value, which is dropped | NO — declared bearer (P8 — State-first lineage); only `weights_version`, with no source id, record count or field names as fields | NO: docstring key list only, no version constant or validator | partial: `result: None` / `signal_detected: False`; inconclusive and no-effect cannot be told apart | none |
| `src/engine/aggregate.py` `aggregate_records` | yes: free-text derivation string (field, n, mean, threshold) | fabricated: 1.0/0.0 copied from the decision | partial: `weights_version` plus count and field inside text; the version is misattributed because the threshold is hardcoded; not the declared bearer | NO: docstring key list only | partial: three null paths exist but share one structured shape | none |
| `src/ui/report.py` `build_report` | yes: passed through from the engine | yes: passed through from the engine (inherits the 1.0/0.0 defect) | NO: priors version only inside `display_text`; not the declared bearer | NO: docstring key list only | partial: "No signal detected" shown for both no-data and below-threshold | none |
| `src/data/schema.py` `validate_and_display` | passthrough of `build_report` | passthrough of `build_report` | NO: same as `build_report` | NO | partial: inherits `build_report` | none |

```
.importlinter                   read
.plumb-line/enforcement.json    read
config/priors.toml              read
src/__init__.py                 read (empty)
src/data/__init__.py            read (empty)
src/data/schema.py              read
src/engine/__init__.py          read (empty)
src/engine/aggregate.py         read
src/services/__init__.py        read (empty)
src/services/source.py          read
src/ui/__init__.py              read (empty)
src/ui/report.py                read

coverage: 12/12 files read, 0 partial, 0 not-read (100%)
principle coverage: P1 — Source-truth layer partial (no source-truth layer declared); all others applied to the full read set
scope note: every in-scope file was read, but the lack of a declared source-truth layer means P1 — Source-truth layer findings cannot be ruled out. This audit does not claim completeness beyond the read set and the checks it could apply.
```

13 findings: 7 violations, 3 needs-review, 3 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

I ran the format checker on the exact report text above, and it passed. The checker input is saved at `<harness>/work/py-broken-1/checker-input.txt`. The import-cycle probe, which ran on a copy of the code, is at `<harness>/work/py-broken-1/probe_imports.py`. The target directory was not changed.

No one was available to answer, so I did not write `plumb-line-audit.md` and did not start `plumb-line-remediate` or `plumb-line-bootstrap`.

## Decisions needed
1. Save this report as `plumb-line-audit.md` in the target? I recommend yes, so the remediation step has a stored input.
2. Hand the findings to `plumb-line-remediate`? I recommend yes, starting with the import cycle in `src/data/schema.py`, because every module fails to load until it is fixed.
3. Run `plumb-line-bootstrap` to name a source-truth layer and make the import rules actually block commits? I recommend yes: the layering violation got through even though the import rules file exists, and until a source-truth layer is named, Principle 1 can only be partly checked.