report-format: v4
scope:               ./fixture
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the owner in the invocation): layers ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors from `config/`; services output is lineage-bearing (source identity, record count, field names, config/version); outputs carry provenance and confidence and propagate the priors version. The owner did not name a source-truth layer, so this audit does not assume one; P1 — Source-truth layer is checked only as "no mock/derived logic in `data`" (none found).

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `fixture/src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | Confidence is a fixed step (1.0 when the mean clears the threshold, 0.0 when it does not), regardless of sample size (n=3) or how close the mean is to the threshold. It encodes a judgment in code, not in `config/`, and a valid "no signal" null result is reported with confidence 0.00, so it reads as "unknown" instead of "confident there is no effect". | Derive confidence from the evidence (n, distance from the threshold) or inject the mapping as a versioned prior. Keep "no signal" separate from "no confidence". | P3 — Confidence + provenance |
| `fixture/src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | The 1.0 and 0.0 confidence levels are unversioned magic numbers next to priors (`signal_threshold`, `stub_confidence`) that do come from `config/priors.toml`. | If these levels are deliberate, move them into `config/priors.toml` next to the other priors. | P5 — Injectable priors |
| `fixture/config/priors.toml` | — | — | needs-review | No code in scope loads `config/priors.toml` into the `config` dict. Every function accepts an injected dict, so the declared rule "priors come from config/" cannot be traced to the file inside this scope. | Add or point to the loader or entry point that reads `config/priors.toml` and passes it in, so the chain from priors file to output `weights_version` can be verified. | P5 — Injectable priors |
| `fixture/src` | — | — | advisory | Adoption gap: no output has a versioned, validated contract (no validator, schema version constant or canonical key list). Contracts are neither declared nor practiced here (P7 — Contracted outputs). | When output shapes stabilise, add a versioned key list and a validator for the services and ui outputs. | P6 — Maturity vocabulary |
| `fixture/src` | — | — | advisory | Adoption gap: no tests and no golden baseline pin any output. Baselines are neither declared nor practiced here (P9 — Golden baseline + explain-the-drift). | Add a golden baseline for `load_and_aggregate` on the stub dataset, with a recorded reason for any drift. | P6 — Maturity vocabulary |

Presence-pass notes (checked, no finding): imports are `ui -> engine` (allowed downward skip), `services -> engine` and `engine -> data`, with no upward imports (P2 — One-way layering), and `.importlinter` enforces the same order. Stub records in `src/services/source.py` are labelled (`data_status: "simulated"`, `"stub source:"` provenance prefix, `lineage.source = "stub/_STUB_RECORDS"`), and confidence is capped by the injected `stub_confidence` (P4 — Quarantined fakery, P3 — Confidence + provenance). `data/schema.py` holds static type maps only (P1 — Source-truth layer). There are no tests, so check 10 has nothing to examine.

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `engine/aggregate.py::aggregate_records` return dict | YES — derivation string with n, threshold, config version | YES — but a fixed step of 1.0 or 0.0 (see findings) | N/A — not the declared bearer; carries `weights_version` | NO — docstring only (adoption gap) | YES — `result: None`, `signal_detected: False` on three paths | NO (adoption gap) |
| `services/source.py::load_and_aggregate` return dict (declared lineage bearer) | YES — `"stub source: …"` and `data_status: "simulated"` | YES — `min(engine, stub_confidence)` | YES — `lineage` has `source`, `record_count`, `field_names`, `config_version` | NO — docstring only (adoption gap) | YES — `result` passes through as None | NO (adoption gap) |
| `ui/report.py::build_report` return dict | YES — passed through from the engine | YES — passed through from the engine | N/A — not the declared bearer; `weights_version` propagated as a structured key | NO — docstring only (adoption gap) | YES — "No signal detected. Result: None" | NO (adoption gap) |

| File | Status |
| ---- | ------ |
| `fixture/src/__init__.py` | read (empty) |
| `fixture/src/data/__init__.py` | read (empty) |
| `fixture/src/data/schema.py` | read |
| `fixture/src/engine/__init__.py` | read (empty) |
| `fixture/src/engine/aggregate.py` | read |
| `fixture/src/services/__init__.py` | read (empty) |
| `fixture/src/services/source.py` | read |
| `fixture/src/ui/__init__.py` | read (empty) |
| `fixture/src/ui/report.py` | read |
| `fixture/config/priors.toml` | read |
| `fixture/.importlinter` | read |
| `fixture/.plumb-line/enforcement.json` | read |
| `fixture/.import_linter_cache/src.meta.json` | read (generated) |
| `fixture/.import_linter_cache/c3f7dc61d873e8291df9c567a548b9ed02a6dbab.data.json` | read (generated) |
| `fixture/.import_linter_cache/.gitignore` | not-read (generated) |
| `fixture/.import_linter_cache/CACHEDIR.TAG` | not-read (generated) |

```
coverage: 14/16 files read, 0 partial, 2 not-read (88%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. The two
not-read files are import-linter cache boilerplate. All 12 source, config and
enforcement files were read.
```

format-validation: scripts/check_report_format.py v6 — clean

5 findings: 0 violations, 3 needs-review, 2 advisory

---

**Summary:** The fixture follows the architecture you declared. It has no upward imports. The service output records the full lineage you asked for (source, record count, field names and config version). The stub data is labelled as simulated and its confidence is capped. The priors version reaches every output. Nothing is a confirmed violation.

What's left to decide:
- **The engine's confidence values (3 needs-review findings):** confidence is hardcoded as 1.0 or 0.0, and nothing in the fixture shows where `config/priors.toml` gets loaded.
- **Missing practices (2 advisories):** no output has a contract, and there are no tests or golden baselines.

`git` couldn't run in this sandbox, and the fixture isn't committed yet, so the commit field says "working tree (uncommitted)".

Should I save this to `plumb-line-audit.md`? I can also hand the findings to `plumb-line-remediate` to apply fixes, which works through them one at a time and shows you a diff for each before changing anything.
