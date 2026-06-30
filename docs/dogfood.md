# Dogfooding

plumb-line is held to its own principles. We applied the `plumb-line-audit`
methodology — the same two-pass audit it tells you to run — to plumb-line's own
first-party source, and recorded exactly what it found and what we did about each
finding.

(An auditor that sniffs out code smells should pass its own smell test.)

Date: 2026-06-29 · Version: v0.1.0
Scope audited: `skills/`, `adapters/`, `primitives/`, `reference/`.
Excluded by design: `examples/` (fixtures are intentionally broken — see
[validation results](validation-results.md)) and generated/vendored files
(lockfiles).

## What the audit found

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| 1 | `adapters/adapter-contract.md:33` | P7 (contract accuracy) | The shared hook I/O contract claimed every guard reads `{ filePath, command }` on stdin. None do: `boundary-guard` reads `{ filePath, importPath }`, `branch-guard` reads `{ filePath }`, and `pre-commit-gate` takes no stdin at all (it reads `PLUMBLINE_TEST_CMD` from the environment). The documented interface did not exist. | **Fixed** — the contract now documents the real per-guard input shapes and carries a contract version. |
| 2 | `primitives/`, `adapters/` outputs | P7 (version anchoring) | No public output shape carried a version constant — not the provenance metadata envelope, not the adapters' `{ allow, reason }` decision. The envelope already has named keys and a validator (`auditMeta` / `audit_meta`), but no version. | **Partial** — declared `PROVENANCE_VERSION` in the primitive (both languages) and versioned the adapter contract. Embedding the version per-output and validating against it is `planned`. |

Two findings, both real, both addressed. The test suites stayed green after the
fixes (primitives 39 JS / 31 Python; adapters 16 JS / 13 Python).

## A note on calibration

The first sweep reported finding #2 as **twelve** separate violations — one per
output-producing function. That is precisely the over-claiming the method guards
against. The audit's calibration rule: a principle adopted *nowhere* in a
codebase is reported **once** as an advisory adoption gap, not N times. Version
anchoring was practiced nowhere, so the honest count is **one** advisory, not
twelve. Collapsing it is the method's under-claiming discipline applied to its
own output — which is the point of recording this at all.

## What was clean

Confirmed by reading context, not keyword matches:

- **P2 (one-way layering)** — no cross-layer imports; `index.mjs` only re-exports
  its siblings.
- **P3 (confidence + provenance) / P4 (quarantined fakery)** — the primitive
  enforces these by construction: taint propagates and cannot be cleared, and
  `auditMeta` flags any laundering. No code hand-builds provenance to bypass the
  law.
- **P5 (injectable priors)** — layers, direction, protected branches, allowlist,
  and the test command are all injected; `STATUS` / `CONFIDENCE` are named
  ordinal lists, not magic priors buried in logic.
- **P9 (drift) / spine (null result)** — no unexplained baselines; the decision
  and checker outputs can all express rejection or an empty result.

## Limits of this audit

This is the methodology applied by a careful reader, not an automated gate. The
automated enforcement plumb-line ships is the lint adapters (ESLint /
import-linter boundaries) and the test suites; this self-audit complements them,
it does not replace them. A finding's absence here means "not found on this
pass," not "provably absent."

## Beyond the fixtures

The auditor has also been run on an unrelated production codebase, where it
surfaced real issues that had passed human review — external corroboration that
the method generalizes beyond plumb-line's own fixtures.

## See also

[validation-results.md](validation-results.md) records the complementary check:
the auditor catching planted violations in the worked fixtures. Validation is the
external test; this is the self-test.

---

## v0.2.0 audit

Date: 2026-06-29 · Version: v0.2.0 · Commit: 4b923f7
Scope: new surface added since v0.1.0 — `primitives/` (scoring resolution, conformance suite), `adapters/*/provenance-lint/` (PB1–PB4 rules, JS + Python), `skills/` (all three).

Four parallel read-only subagents ran the two-pass audit across the four areas; findings were synthesised and calibrated here.

### What the audit found

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| 1 | `primitives/conformance/cases.json` (SPEC §7 vs §5) | P7 — contracted outputs | Conformance §7 defines conformance as "all cases in `cases.json`", but `cases.json` had no cases for checker conditions #5 (dropped taint) and #6 (unreproducible) declared in SPEC §5. A new-language port could silently omit detection of these two conditions and pass the full conformance suite. | **Fixed** — added one conformance case for each missing condition. |
| 2 | `primitives/conformance/cases.json` (spine) | Spine + P7 | Null-envelope (`null → ["missing meta"]`) and empty-envelope (`{} → []`) checker behaviors — documented in SPEC §5's totality requirement and previously caught as a real cross-language divergence (PARITY.md) — had no conformance cases pinning them. Fixes in code were not machine-enforced. | **Fixed** — added two conformance cases; a regression in any implementation or new port now fails the suite. |
| 3 | `adapters/python/provenance_lint.py:117` | P8 — state-first lineage | `check(source, filename)` accepted `filename` as a key input condition but returned issue dicts without it (`{'line', 'rule', 'message'}` only). The filename was present in `main()`'s print output but stripped from the programmatic API — callers using `check()` directly got self-describing issues with no file attribution. | **Fixed** — `check()` now returns `{'line', 'rule', 'message', 'filename'}` for every issue, including parse errors. |
| 4 | `adapters/python/provenance_lint.py:23` | P5 — injectable priors | `CLEAN_SOURCES = {'real', 'semiReal', 'fallback'}` was a locked-in module constant with no injection path. The JS mirror exposes this via `opts.sources`, making it per-project configurable. Python projects using a non-standard source vocabulary had to patch source. | **Fixed** — `check()` now accepts `clean_sources=None`; defaults to `CLEAN_SOURCES` if unset. The `_Visitor` stores it as an instance attribute. |
| 5 | `primitives/python/__init__.py:30` | P6 — maturity vocabulary | `reset_step_counter` was listed in `__all__` alongside production API functions with no maturity signal. A production consumer has no reliable indication this is test-only infrastructure. | **Fixed** — removed from `__all__`; added a comment in both `__init__.py` and `provenance.py` / `provenance.mjs` marking it as test-only. Still importable by test suites from the module directly. |
| 6 | `primitives/SPEC.md:3` | P6 — maturity vocabulary | The SPEC's status line read `**Status:** stable`. "Stable" is not a P6 vocabulary term (`current / partial / mock / planned / not-implemented`). A reader applying the vocabulary to this document would not recognise it. | **Fixed** — changed to `current`; schema-version stability recorded as a parenthetical ("stable — no breaking changes planned") to preserve the distinct schema-version claim. |
| 7 | `primitives/README.md` status table | P7 — contracted outputs | Per-output `PROVENANCE_VERSION` embedding (labeled `planned` in the v0.1.0 dogfooding report) and a forthcoming `validateEnvelope` structural checker were absent from the README status table. A reader of README alone could not see these planned gaps. | **Fixed** — added two `planned` rows to the status table. |
| 8 | `skills/plumb-line-audit/SKILL.md`, `skills/plumb-line-bootstrap/SKILL.md`, `skills/plumb-line-method/SKILL.md` | Spine + P4 — quarantined fakery | All three skills open with "REQUIRED READING FIRST: `reference/portable-principles.md`" but none specified what to do if the file is unreadable. Without a stop condition, the model falls back on training-data recollection — teaching from, or auditing against, an approximate or stale version of the principles without labelling it as such. A wrong or stale principles version produces silently wrong audit findings. | **Fixed** — added an explicit stop-and-report instruction to all three skills: if the principles file cannot be read, the skill must stop and report the file as missing rather than continue from memory. |

Eight findings; all fixed. Test suites stayed green after all changes (primitives: 67 JS / 45 Python; adapters: 32 JS / 21 Python).

### Calibration note

Findings 1 and 2 are from the same file — they are listed separately because they represent distinct principles (P7 contracted-output coverage vs. spine null-result enforcement) with different failure modes. Both are cases where the omission pass caught what the presence pass cannot: an absence has no smell to grep.

### What was deferred (documented, not fixed)

These findings were real but required design decisions beyond the scope of a dogfooding pass. Each is recorded so it cannot be silently dropped, and each is tracked as a GitHub issue ([#23](https://github.com/effythealien/plumb-line/issues/23)–[#29](https://github.com/effythealien/plumb-line/issues/29), label `audit-deferral`).

| # | Location | Principle | Finding | Status |
| - | -------- | --------- | ------- | ------ |
| [D1](https://github.com/effythealien/plumb-line/issues/23) | `primitives/js/provenance.mjs:85`, `primitives/python/provenance.py:13` | Spine | Module-level mutable step counter. In any concurrent setting (Node worker threads, Python async event loops, parallel test runners) step IDs can collide or become non-monotonic. The `__resetStepCounter`/`reset_step_counter` test helpers are a paper cover, not a fix. Lineage step IDs are the backbone of P8 reproducibility; unreliable IDs undermine the audit trail. | Documented. Fix requires a context-local counter passed through the call chain, or a per-combine UUID — a meaningful API change. |
| [D2](https://github.com/effythealien/plumb-line/issues/24) | `primitives/python/marked.py:2–5`, `audit.py:3–5` | P1 | The `try: from .provenance import … except ImportError: from provenance import …` dual-import shim resolves the source-truth module at runtime. If a consumer's project has a top-level `provenance.py`, the installed package version can be silently displaced. | Needs review. Risk is narrow while the installed package is the primary path; review when the flat-import path is documented as supported. |
| [D3](https://github.com/effythealien/plumb-line/issues/25) | `primitives/js/provenance.mjs:117–126`, `primitives/python/provenance.py:77–108` | Spine + P8 | `combineProvenance()` with zero inputs yields `{source: "derived", lineage: []}`. The SPEC mandates this (§3). Running `auditMeta` on this output flags it as `"unreproducible: derived value has no lineage"` (SPEC §5 condition 6). The two SPEC sections are in direct contradiction for this edge case. The cross-check is not in the conformance suite. | Design decision required: either assign `source: "unavailable"` to the zero-input case or add an explicit audit exemption. Documented in SPEC §3/§5. |
| [D4](https://github.com/effythealien/plumb-line/issues/26) | `primitives/js/marked.mjs:35–49`, `primitives/python/marked.py:21–29` | P8 | `derive()` records input provenance states in lineage but does not record the transformation function `fn` itself. Two calls to `derive` with identical inputs but different `fn`s produce identically-shaped lineage. The `basis` override is the escape hatch for callers needing full reproducibility, but it is undocumented as the convention. | Advisory. `fn` identity is out of scope for envelope schema version 1. Document `basis` as the operation-label convention in SPEC/README. |
| [D5](https://github.com/effythealien/plumb-line/issues/27) | `primitives/js/audit.mjs`, `primitives/python/audit.py` | P7 | `auditMeta({})` returns `[]` (no issues) for a structurally empty envelope missing all four required fields. The SPEC mandates this (§5 totality). But it means the "validator" checks logical consistency among claimed fields, not that required fields are present. A companion `validateEnvelope` structural checker is needed to complete P7. | Planned — added to README status table as `planned`. |
| [D6](https://github.com/effythealien/plumb-line/issues/28) | `skills/plumb-line-audit/SKILL.md:73–77`, `skills/plumb-line-bootstrap/SKILL.md:109–112` | P7 + P8 | The audit report format specifies `file:line`, `Pn`, description, direction, and summary count — but no required header (scope, principles-doc version, audit date, git SHA). A stored audit report cannot be re-verified or reproduced without knowing what was audited against which version of the rules. The bootstrap step 5 report has the same gap. Neither format has a version constant. | Planned. Adding a required header block and `report-format: v1` to the audit and bootstrap report specs is the direction. |
| [D7](https://github.com/effythealien/plumb-line/issues/29) | `adapters/python/provenance_lint.py:24–25`, JS mirror | P5 | `PRIMITIVE_MODULES` and `TRACKED` (the lists of primitive module names and tracked function names) are hardcoded with no injection path. A project using a re-export or wrapper module cannot extend coverage without patching source. | Needs review. Arguably definitional coupling to the library's API; at minimum these should be documented as version-pinned to the primitive's public API contract. |

### What was clean

Confirmed by reading, not keyword matches:

- **P2 (layering)** — no upward imports in the new surface; the provenance-lint adapters correctly live in `adapters/` with no cross-layer calls.
- **P3 + P4** — the new PB1–PB4 static lint rules correctly target only resolved primitive call sites on literal values; dynamic values are left alone (under-claim over false positives). No escaped mock data found.
- **P5** — no magic numbers in the new combinator functions; `confidenceScore` bounds (`[0,1]`) are mathematical, not policy; the `min` combination rule is the maximally conservative non-assumption.
- **P6** — all new code in `primitives/README.md` and the conformance suite uses P6 vocabulary correctly; the adapters' "may move to primitives/ in a future version" note is an advisory (not a P6-term violation) at the advisory level.
- **P9** — `conformance/cases.json` is a genuine golden baseline for `combineProvenance` and `auditMeta`; the new cases add to it rather than changing it.
- **Spine** — all scalar utility functions (`weakestSource`, `combineConfidenceScore`, `weakestConfidence`) correctly return `undefined`/`None` for genuinely absent results rather than collapsing to a default.
