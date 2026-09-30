report-format: v4
scope:               fixture/ (repository)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

**Principle glossary**

```
P1 — Source-truth layer        P6 — Maturity vocabulary
P2 — One-way layering          P7 — Contracted outputs
P3 — Confidence + provenance   P8 — State-first lineage
P5 — Injectable priors         P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

**Declared architecture (as supplied by the owner in the invocation):** layers `ui -> services -> engine -> data`, one-way, non-adjacent downward skips allowed (P2 — One-way layering); priors come from `config/` (P5 — Injectable priors); the services layer is the lineage-bearing output (source identity, record count, field names, config/version) (P8 — State-first lineage); outputs carry provenance and confidence and propagate the priors version (P3 — Confidence + provenance). No source-truth layer was named, so P1 — Source-truth layer is not inferred and its coverage is partial (see the advisory below).

**Findings**

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/engine/aggregate.py` | 64 | `aggregate_records` | needs-review | Confidence is a hardcoded binary (`1.0` if mean ≥ threshold, else `0.0`). It ignores record count and margin, so 3 records just over the threshold report full certainty, and a measured below-threshold result reports zero confidence in the null. `ui/report.py` passes this uncapped value straight to display; only the services path caps it at `stub_confidence`. | Derive confidence from the evidence (n, margin to threshold), or inject its policy from `config/priors.toml`. Keep confidence in a null result separate from "signal detected". | P3 — Confidence + provenance |
| `src/engine/aggregate.py` | 28-49 | `aggregate_records` | needs-review | "No records" and "no numeric values" (inconclusive) return the same structured shape as a measured "no signal" (`signal_detected: False`, `result: None`, `confidence: 0.0`). The only difference is free text in `provenance`. `src/ui/report.py:30-33` then shows "No signal detected" for empty input, so an inconclusive result reads as a negative finding. | Add a structured outcome key (e.g. `status: detected / not_detected / inconclusive`) and render inconclusive separately in the UI. | spine — null-result expressibility |
| `src/services/source.py` | 3, 20 | `load_and_aggregate` | needs-review | The module docstring calls this a "Fetch/persist boundary" that "loads raw records from a data source", but nothing is fetched or persisted: the records are the in-code `_STUB_RECORDS`. The output is correctly labelled (`data_status: "simulated"`, provenance prefixed "stub source"), so this is limited to the docstrings. | Say in the docstrings that it is a stub with no persistence, e.g. "stub — fetch/persist planned". | P6 — Maturity vocabulary |
| — | — | — | advisory | No source-truth layer is declared (the invocation, `.importlinter` and `.plumb-line/enforcement.json` give only layer order). Checks against P1 — Source-truth layer are therefore partial: the audit cannot say whether the stub records in `services/` belong in a declared truth layer. | Declare the source-truth layer in a ruleset file (`plumb-line-bootstrap`, declaration-only entry). | P6 — Maturity vocabulary |
| — | — | — | advisory | Adoption gap: no output shape has a versioned, validated contract (no validator, version constant or canonical key list). Neither declared nor practiced anywhere, so reported once. | Add a contract version plus a key list and validator for the services output first. | P7 — Contracted outputs |
| — | — | — | advisory | Adoption gap: there are no tests or golden baselines anywhere in scope, so no output is pinned and drift cannot be detected. Reported once. | Pin `load_and_aggregate` output under `config/priors.toml` v1.0.0 as a golden baseline, with a drift-explanation convention. | P9 — Golden baseline + explain-the-drift |

Presence-pass notes (checked, no finding): imports are `ui -> engine`, `services -> engine` and `engine -> data`, all downward, and the `ui -> engine` skip is allowed; `.importlinter` enforces the same order (P2 — One-way layering). `signal_threshold` and `stub_confidence` are injected from `config/priors.toml` (P5 — Injectable priors). Stub data is labelled `simulated`, and its confidence is capped rather than raised.

**Omission pass**

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/engine/aggregate.py` `aggregate_records` | yes — free-text derivation string | yes, but binary 1.0/0.0 (needs-review) | n/a — not the declared bearer; count and version appear only in provenance text, plus `weights_version` | NO — adopted nowhere (advisory) | partial — `result: None` for no signal; inconclusive collapsed into no-signal (needs-review) | NO — none in repo (advisory) |
| `src/services/source.py` `load_and_aggregate` | yes — "stub source: …" plus `data_status: simulated` | yes — capped by injected `stub_confidence` | yes — `lineage` has source, record_count, field_names, config_version | NO — adopted nowhere (advisory) | partial — passes `result: None` through; inherits the engine's inconclusive collapse | NO — none in repo (advisory) |
| `src/ui/report.py` `build_report` | yes — passed through from the engine | yes — passed through uncapped from the engine | n/a — not the declared bearer; bypasses services via an allowed skip; `weights_version` propagated | NO — adopted nowhere (advisory) | partial — renders "No signal detected"; empty input shown the same way | NO — none in repo (advisory) |

**Coverage map**

| File | Status |
| ---- | ------ |
| `src/__init__.py` | read |
| `src/data/__init__.py` | read |
| `src/data/schema.py` | read |
| `src/engine/__init__.py` | read |
| `src/engine/aggregate.py` | read |
| `src/services/__init__.py` | read |
| `src/services/source.py` | read |
| `src/ui/__init__.py` | read |
| `src/ui/report.py` | read |
| `config/priors.toml` | read |
| `.importlinter` | read |
| `.plumb-line/enforcement.json` | read |
| `.import_linter_cache/.gitignore` | read |
| `.import_linter_cache/src.meta.json` | read |
| `.import_linter_cache/CACHEDIR.TAG` | not-read (generated cache) |
| `.import_linter_cache/c3f7dc61d873e8291df9c567a548b9ed02a6dbab.data.json` | not-read (generated cache) |

```
coverage: 14/16 files read, 0 partial, 2 not-read (88%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. All
source, config and enforcement files were read; the two unread files are
generated import-linter cache. P1 — Source-truth layer coverage is partial
(no declared source-truth layer). The import-linter contract was read but not
executed; git history was unavailable (git not runnable in this sandbox).
```

format-validation: scripts/check_report_format.py v6 — clean

6 findings: 0 violations, 3 needs-review, 3 advisory

---

There are no confirmed violations. The declared rules all hold: imports only go down the layers, priors come in from `config/`, and the services output records its full lineage and labels its data as simulated. The three needs-review items are about the engine's all-or-nothing confidence score, empty input being reported as "no signal", and a docstring that says the stub fetches and saves data. The three advisories are adoption gaps.

Next steps:
- **Save the report:** I can write it to `plumb-line-audit.md`.
- **Apply the fixes:** I can hand the findings to `plumb-line-remediate`, which shows you a diff for each fix before changing anything.
