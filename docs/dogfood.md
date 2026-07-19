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
| [D4](https://github.com/effythealien/plumb-line/issues/26) | `primitives/js/marked.mjs:35–49`, `primitives/python/marked.py:21–29` | P8 | `derive()` records input provenance states in lineage but does not record the transformation function `fn` itself. Two calls to `derive` with identical inputs but different `fn`s produce identically-shaped lineage. The `basis` override is the escape hatch for callers needing full reproducibility, but it is undocumented as the convention. | **Resolved in #26 (PR #79).** `basis` documented as the operation-label convention in SPEC §4, `primitives/README.md`, and the `derive` docstrings; `fn` identity stays out of scope for schema version 1. |
| [D5](https://github.com/effythealien/plumb-line/issues/27) | `primitives/js/audit.mjs`, `primitives/python/audit.py` | P7 | `auditMeta({})` returns `[]` (no issues) for a structurally empty envelope missing all four required fields. The SPEC mandates this (§5 totality). But it means the "validator" checks logical consistency among claimed fields, not that required fields are present. A companion `validateEnvelope` structural checker is needed to complete P7. | **Resolved in #27 (PR #54).** `validateEnvelope` / `validate_envelope` added (SPEC §5a, `validate` conformance kind); README maturity row promoted `planned` → `current`. |
| [D6](https://github.com/effythealien/plumb-line/issues/28) | `skills/plumb-line-audit/SKILL.md:73–77`, `skills/plumb-line-bootstrap/SKILL.md:109–112` | P7 + P8 | The audit report format specifies `file:line`, `Pn`, description, direction, and summary count — but no required header (scope, principles-doc version, audit date, git SHA). A stored audit report cannot be re-verified or reproduced without knowing what was audited against which version of the rules. The bootstrap step 5 report has the same gap. Neither format has a version constant. | **Resolved in #28 (PR #78).** Both report specs now require a `report-format: v1` header block (scope, `principles-revision`, date, commit); `reference/portable-principles.md` carries a `Principles revision` stamp for it to cite. |
| [D7](https://github.com/effythealien/plumb-line/issues/29) | `adapters/python/provenance_lint.py:24–25`, JS mirror | P5 | `PRIMITIVE_MODULES` and `TRACKED` (the lists of primitive module names and tracked function names) are hardcoded with no injection path. A project using a re-export or wrapper module cannot extend coverage without patching source. | Needs review. Arguably definitional coupling to the library's API; at minimum these should be documented as version-pinned to the primitive's public API contract. |

### What was clean

Confirmed by reading, not keyword matches:

- **P2 (layering)** — no upward imports in the new surface; the provenance-lint adapters correctly live in `adapters/` with no cross-layer calls.
- **P3 + P4** — the new PB1–PB4 static lint rules correctly target only resolved primitive call sites on literal values; dynamic values are left alone (under-claim over false positives). No escaped mock data found.
- **P5** — no magic numbers in the new combinator functions; `confidenceScore` bounds (`[0,1]`) are mathematical, not policy; the `min` combination rule is the maximally conservative non-assumption.
- **P6** — all new code in `primitives/README.md` and the conformance suite uses P6 vocabulary correctly; the adapters' "may move to primitives/ in a future version" note is an advisory (not a P6-term violation) at the advisory level.
- **P9** — `conformance/cases.json` is a genuine golden baseline for `combineProvenance` and `auditMeta`; the new cases add to it rather than changing it.
- **Spine** — all scalar utility functions (`weakestSource`, `combineConfidenceScore`, `weakestConfidence`) correctly return `undefined`/`None` for genuinely absent results rather than collapsing to a default.

---

## v0.3.1 dogfood self-audit

Date: 2026-07-01 · Diff: `v0.3.0..main` method surface (the zero-input
`source:"unavailable"` fix, per-combine lineage renumbering, ESLint dep swap).
Run as Part 2 of the `docs/release-harness.md` cycle.

**Code changes audited as honest improvements, not violations:**
- **P3 (laundered uncertainty) — improved.** Zero-input previously returned
  `source:"derived"` with empty lineage, an envelope that *fails its own §5
  audit*; the new `"unavailable"` audits clean.
- **P8 (lineage) — strengthened.** Per-combine renumbering makes step IDs
  unique-within-output (§4) and a pure function of structure; the old global
  counter could mint duplicate IDs across two independently-built envelopes.
- **P9 (baseline drift) — explained.** The changed golden value in `cases.json`
  ships with the SPEC §3 rewrite, a new audit case, and a CHANGELOG entry.
- **P5/P6** clean — `step-${i+1}` is an identifier scheme, not a tunable prior;
  the deprecated reset no-ops are honestly labelled.

**One finding, resolved in place (not deferred):**

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| G1 | `primitives/SPEC.md` §1 + zero-input fix | P6 / governance | By the letter of SPEC §1, changing the combination law's result for an existing case MUST bump `PROVENANCE_VERSION`; the zero-input fix does exactly that while staying at v1. The SPEC asserted a rule the diff appeared to violate (and the header still claimed "stable — no breaking changes planned"). | **Fixed in place.** Amended SPEC §1 with a narrow carve-out: correcting a result another normative section already flags as inconsistent is a *conformance fix*, not breaking, and MUST NOT bump the version (guarded by mandatory CHANGELOG + ADR + conformance case). Recorded in [ADR-0008](adr/0008-zero-input-conformance-fix-no-wire-bump.md). Dropped the header maturity over-claim. `PROVENANCE_VERSION` stays `1`; v0.3.1 stays a patch. |

No deferrals this cycle.

## v0.4.0 dogfood self-audit

Date: 2026-07-01 · Version: v0.4.0 · Diff: `v0.3.1..HEAD` (`881f3fd`)
Applied `plumb-line-audit` to the v0.4.0 method-surface diff (the new
`validateEnvelope`/`validate_envelope` checker + conformance `validate` kind, the
`report-format: v1` header, the `basis` convention docs, and the SPEC changes).
Non-blocking per `docs/release-harness.md`.

**Verified clean (no finding):** `validateEnvelope`/`validate_envelope` are at
full parity — identical messages, canonical camelCase field labels in both
languages, both total; conformance report 23/23. SPEC §5a and §4 are internally
coherent with the implementations (validator checks presence + type only, not
enum membership; `basis` is advisory everywhere it appears). The `report-format:
v1` header block is consistent across both skills and cites the new
`Principles revision: 1` stamp. README maturity flip `planned → current` is
earned, not an over-claim (P6).

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| G1 | `primitives/PARITY.md:8` | P8 / P9 | Pinned suite count read `JS 89/89`, but the true figure is **98/98** — v0.4.0 adds the fast-check `property.test.mjs` (9 tests). The `89` was measured without `fast-check` installed, so that suite silently failed to import while vitest still printed "89 passed" — the number both undercounted and masked a non-running suite. | **Fixed in place.** Verified `npm ci && npx vitest run` → 98/98; corrected the count, added a reproduce-don't-hand-type note, and documented the fast-check dependency. |
| G2 | `primitives/PARITY.md` / `property.test.mjs` | P6 / parity | Property tests (fast-check) are JS-only; Python has no `hypothesis` mirror, widening the JS/Python suite gap (98 vs 59). | **Fixed in place (documented).** Added a PARITY note that property tests are JS-only and sit *outside* the `cases.json` conformance contract — law/checker parity is still data-enforced. A Python hypothesis mirror is possible future work. |
| G3 | `primitives/python/audit.py` | Spine (totality) | Pre-existing, **out of v0.4.0 scope**: `audit_meta` guards `if meta is None`, so a falsy-but-not-None input (`0`, `''`, `False`) falls through and raises `AttributeError`, whereas JS `auditMeta` guards `if (!meta)` and returns `["missing meta"]`. SPEC §5 requires the checker be total. The new `validate_envelope` does **not** share this gap. | **Deferred → [#80](https://github.com/effythealien/plumb-line/issues/80)** (`audit-deferral`). Not introduced by this release; tracked for a totality-parity fix + conformance case. |

## v0.4.1 dogfood self-audit

Date: 2026-07-02 · Version: v0.4.1 · Commit: `6adb54b` ·
Scope: the method-surface diff `v0.4.0..HEAD` (`primitives/`, `skills/`,
`reference/portable-principles.md`, `examples/AUDIT-EXPECTATIONS.md`, CHANGELOG,
ADR-0009).

**Result: clean — 0 violations, 2 needs-review (both benign on inspection).**

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| H1 | `docs/adr/0009-…` (Consequences) | (process) | The residual JS `Map`/`Date`/class-instance divergence is explicitly named, filed as [#96](https://github.com/effythealien/plumb-line/issues/96) (`audit-deferral`), and reasoned as unencodable in `cases.json`. Not a finding — the deferral discipline worked as intended. | No action. |
| H2 | `reference/portable-principles.md:11` | P9 (needs-review) | `principles-revision` stays `1` while report-format moves v1→v2. Defensible: the file scopes revision bumps to a principle's meaning/scope/vocabulary, and no principle wording changed; all surfaces moved to v2 in lockstep (no drift). | No change; judgment recorded here. |

**Clean:** no laundered uncertainty (P3), boundary leaks (P2), hardcoded priors
(P5), overstated maturity (P6 — CHANGELOG/ADR language is precise), missing
lineage (P8 — no new outputs), or escaped fakery (P4). The auditor re-verified
the parity gate live (`report.mjs` → 26/26, CONFORMANT).

## v0.5.0 dogfood self-audit

Date: 2026-07-03 · Version: v0.5.0 · Commit: `4461f38` (+ dogfood polish) ·
Scope: the method-surface diff `v0.4.1..HEAD` — the `plumb-line-audit`
coverage-honesty + spine-calibration change (report-format v2→v3), the bootstrap
header bump, `reference/portable-principles.md`, `examples/AUDIT-EXPECTATIONS.md`,
and CHANGELOG (#87, #101). The range's other unreleased work is infra-only
(OpenSSF-badge configs, coverage pragmas, lockfiles; no principle-bearing logic,
`PROVENANCE_VERSION` unchanged) and out of dogfood scope.

**Result: clean — 0 violations, 2 needs-review (both fixed in place).**

Self-application angles verified: the coverage-map change genuinely *mandates* the
new artifact (Report §4 + the format-FAIL gate), not merely describes it, and the
"four parts ↔ §§1–4" skeleton is internally consistent — it closes the coverage
overstatement it targets with no new contradiction. All four normative surfaces
read `v3` in lockstep; residual `v1`/`v2` strings are legitimately historical. The
spine block downgrades an always-accept stub to needs-review only where rejection
is neither declared nor practiced, preserving the confirmed-violation path
elsewhere — matching the `AUDIT-EXPECTATIONS.md` answer key.

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| J1 | `skills/plumb-line-audit/SKILL.md` (coverage-honesty ¶) | P6 (needs-review) | The new paragraph wrote "honest-denominator **spine**", overloading the reserved term "spine" (elsewhere = null-result expressibility). | **Fixed in place** → "honest-denominator **discipline**"; "spine" reserved for the null-result concept. |
| J2 | `skills/plumb-line-bootstrap/SKILL.md:110–120` | P7 (needs-review) | Bootstrap stamps `report-format: v3` but emits only the header, not the 4-part audit body; the shared version spanned two report shapes with no note. | **Fixed in place** — added a line stating bootstrap shares the v3 **header block** only; glossary/findings/coverage-map are audit-specific. |

**principles-revision correctly stays `1`** (no principle meaning, scope, or
vocabulary changed) — same judgment as H2, recorded in the CHANGELOG.

## v0.5.1 dogfood self-audit

Date: 2026-07-03 · Version: v0.5.1 · Commit: `7bf38b9` · Scope: the method-surface
diff `v0.5.0..HEAD` (#88 audit handoff, #89 method/bootstrap onboarding) plus the
ROADMAP/CHANGELOG reconciliation.

**Result: clean — 0 findings.**

The self-audit verified the angles that matter for this change:
- **The new audit handoff stays genuinely read-only** — "OFFER — do not perform",
  "produces a plan, not edits", "the auditor applies nothing itself". It never
  implies it fixes anything (P-consistency with "review you can trust does not
  mutate").
- **`plumb-line-remediate` is labelled `planned` everywhere** it appears (SKILL,
  CHANGELOG, ROADMAP) — no maturity over-claim of an unbuilt skill (P6).
- **The first-run-flow claim is accurate** — a marketplace plugin registers skills
  but cannot auto-execute one on install; the claim is scoped precisely to that.
- **The ROADMAP reconciliation discloses the 0.5.0 descope rather than hiding it** —
  v0.5.0 is marked "shipped (partial)" with an explicit "the other two planned
  themes did NOT make 0.5.0" note. This is the overstated-maturity failure the
  project exists to catch, avoided on its own release notes.
- No bare `P#` and no report-format drift in the changed skill text.

**Closure:** the v0.4.0 dogfood deferral **G3 → [#80](https://github.com/effythealien/plumb-line/issues/80)**
(the `audit_meta` totality/parity gap) is the bug **fixed** in this release.

## v0.6.0 dogfood self-audit

Date: 2026-07-05 · Scope: diff `v0.5.1..5b5355c` (the v0.6.0 method-surface
release diff — skills, adapters lint, examples harness, manifests, docs) ·
Principles revision: 1 · Coverage: 20/21 diff files read, 1 partial (a brand
SVG whose unread tail mirrors a fully-read sibling).

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| 1 | `README.md:106` | P6 — Maturity vocabulary | Status section still said "the three skills" while the rest of the README and both plugin manifests say four — a merge-resolution artifact contradicting the release this diff prepares (violation) | **Fixed** — count corrected in the harness-fixes pass |
| 2 | `skills/plumb-line-method/SKILL.md:36` | P6 — Maturity vocabulary | Code sample taught `derivedFromMock … impossible to clear`; the threat model claims tamper-*evident* only — "impossible" overstates the guarantee (needs-review) | **Fixed** — now "no API exists to clear it", matching the threat model and bootstrap's framing |
| 3 | `adapters/js/provenance-lint/README.md:49–51` | P6 — Maturity vocabulary | "Python parity: same semantics" overstated the #29 injection path — JS `modules` matches import specifiers exactly, Python `extra_modules` matches basenames (needs-review) | **Fixed** (wording — the divergence is now stated explicitly) + **Deferred** (behavior alignment) → [#138](https://github.com/effythealien/plumb-line/issues/138) |
| 4 | `examples/REMEDIATE-EXPECTATIONS.md` History | P8 — State-first lineage | Harness history entries recorded date + outcome but not the commit/skill revision they were scored against — a tag-unblocking record that could not be tied to the exact SKILL.md it validated (needs-review) | **Fixed** — every history entry now records the commit SHA and principles revision |
| 5 | `report-format` / `remediation-format` | P7 — Contracted outputs | Version constant + canonical key list exist, validator does not — and remediate consumes reports downstream (advisory adoption gap, reported once) | **Deferred** → [#139](https://github.com/effythealien/plumb-line/issues/139) |

Clean on the rest of the diff by the auditor's own account: the lint injection
path is additive with fail-loud config errors (spine/P5 done right), all new
roadmap/README direction text carries explicit `planned` labels, the
remediation record gives remediation its own lineage by design, and the v0.5.0
milestone re-scoping is disclosed rather than backfilled.

Meta-note, recorded because the project's honesty applies to its process too:
finding 1 (and the same-day py-clean fixture FAIL in the validation record) were
both introduced or missed by the same maintainer+agent pass that built the
release — and both were caught by the harness, not by re-reading. That is the
harness doing exactly what it exists to do.

## v0.7.0 dogfood self-audit

Date: 2026-07-11 · Scope: diff `v0.6.0..f8773fb` (the wire-v2 method-surface
release diff — primitives, SPEC, conformance, bundled primitive, bootstrap
Step 4b, scripts) · Principles revision: 1 · Coverage: 24/56 diff files read, 4
partial, 28 not-read (~43%; the not-read set was triaged to test-only diffs and
non-provenance infra/governance files — an honest denominator, not a
completeness claim).

The core new surface — the content-addressed id scheme, the version field +
read policy, the `inferred` rung, and the bundled primitive — came back
**clean** on the provenance model: every new output category carries the fields
the project's own conventions require (`stepId`/`step_id` is reproducible and
pinned by cross-language golden vectors; the version policy is documented in
SPEC §5b and conformance-pinned; the bundle's second-source-of-truth risk is
guarded by both a byte-identity drift check and a behavioral conformance check).
The `primitives/README.md` "planned → current" maturity-table edit is itself
correct self-application of P6.

The auditor found one recurring drift, turned on plumb-line's own docs:

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| 1 | `SECURITY.md:57,64` | P6 / P9 | Security-facing doc still said "envelope schema version 1 (`PROVENANCE_VERSION = 1`)" and the SPEC §6 out-of-scope carve-out still cited "version 1" — a factually wrong claim about the wire version this release ships (violation) | **Fixed** — both → version 2 |
| 2 | `README.md:73,106` | P6 | Top-level README (most visible doc) described the spec as "envelope schema version 1" in two places, the version this release supersedes (violation) | **Fixed** — both → version 2 |
| 3 | `primitives/README.md:13`, `primitives/js/README.md:23`, `primitives/python/README.md:23` | P6 | Three package READMEs carried the stale "(envelope schema version 1)" spec reference (violation) | **Fixed** — all → version 2 |
| 4 | `primitives/conformance/README.md:28,31,38` | P9 | The self-certification doc's example badge (`plumb-line v1`) and certification prose contradicted the tool it documents — `report.mjs` now generates a `v2` badge — so a new implementer would publish a stale badge (violation) | **Fixed** — badges + prose → v2 |
| 5 | `docs/threat-model.md:91` | P9 | N4's "out of scope for envelope schema version 1 (SPEC §6)" cross-reference drifted from SPEC §6, now version 2 (violation) | **Fixed** → version 2 |
| 6 | `primitives/js/audit.mjs`, `primitives/python/audit.py` (version-read branches) | P3 | A non-numeric `provenanceVersion` (e.g. string `"2"`) matches neither the legacy nor future branch, so no advisory is emitted — untested, differs from the documented "read on every call" policy (needs-review) | **Deferred** → [#156](https://github.com/slopstopper/plumb-line/issues/156) |

All five confirmed findings are the **same failure class** — a version reference
that should have moved with `PROVENANCE_VERSION` 1→2 but didn't, across docs
untouched by the wire-v2 diff. This is exactly the drift P9 exists to catch,
turned on plumb-line's own documentation; none touch runtime behavior or the
conformance suite (both version-correct and tested). A repo-wide sweep confirmed
no other live "schema version 1" reference remains (the one in this file's D4
row is a historical record of a past scope decision, correctly left as-is).

Meta-note: the bump populated the three manifests and `SPEC.md` but not the
seven prose copies of the version — a bump-script blind spot. Filed as a
harness improvement candidate: grep for `schema version <N-1>` after any wire
bump (recorded here rather than lost; a checklist item belongs in
`RELEASING.md`/`bump-version.mjs`).

---

## v0.7.1 dogfood self-audit — 2026-07-12

Ran the `plumb-line-audit` method on plumb-line's own v0.7.1 diff
(`c4132a0..HEAD`), lens on P6 (maturity honesty) and P9-style drift — where
dogfooding historically finds things. One confirmed violation, **fixed before the
tag**; three advisory items filed as tracking issues.

| # | Location | Principle | Finding | Resolution |
| --- | --- | --- | --- | --- |
| 1 | `adapters/js/provenance-lint/require-provenance-output.cjs` (local classification) | P6 | **Confirmed violation.** The JS rule classified locals only from `const/let x =` declarators, ignoring a later plain `out = ...` reassignment — so `let out = x*r; out = mark(out); return out` was flagged as untagged even though `out` **was** tagged. A real false positive, contradicting the "zero-false-positive by design" claim in CHANGELOG/README/ADR-0011. Verified by executing the rule (not just reading it). Python's parallel checker guarded this via pop-on-reassignment; JS did not. | **Fixed** (commit `d2edf49`) — JS now tracks every value-binding assignment (declarator + plain `x = …`) and demotes any name assigned >1× to unknown, mirroring Python. Mirrored regression fixtures added both suites. |
| 2 | `adapters/js/provenance-lint/README.md` | P9-ish | JS README says the rule "drops straight into `pre-commit-gate`," but only Python has a test proving that wiring — implies symmetric demonstrated integration (advisory). | **Deferred** → [#163](https://github.com/slopstopper/plumb-line/issues/163) |
| 3 | `eslint-provenance.template.cjs`, bootstrap/remediate skills, root README | P6 (self-application) | New rule shipped but not wired into the project's own onboarding path — a bootstrap user would never discover it (advisory adoption gap). | **Deferred** → [#164](https://github.com/slopstopper/plumb-line/issues/164) |
| 4 | `primitives/SPEC.md` §5 | P9-ish | The #96 non-plain-object wording reads as uniform, but Python `isinstance(meta, dict)` accepts dict subclasses while JS rejects non-plain objects — slight parity overclaim (needs-review). | **Deferred** → [#165](https://github.com/slopstopper/plumb-line/issues/165) |

The confirmed finding is exactly what this pass exists to catch: a shipped,
documented-as-zero-FP checker that *wasn't* — surfaced by running the method on
our own diff, after per-task and whole-branch reviews both missed the
false-positive direction of the reassignment gap. Fixed before the tag; the
mechanical version-prose sweep (the v0.7.0 P9 class) came back clean.

---

## v0.7.2 dogfood self-audit — 2026-07-15

Ran the `plumb-line-audit` method on plumb-line's own v0.7.2 diff
(`d933c4c..HEAD`), lens on P6 (maturity honesty) and P9-style drift. **0 confirmed
violations; 5 advisory doc/comment-drift items — all fixed before the tag** (commit
`8bd305f`). The shipped mapping code is correct and matches its own fixture + CI guard.

| # | Location | Principle | Finding | Resolution |
| --- | --- | --- | --- | --- |
| 1 | `ROADMAP.md` #92 | P6 | Roadmap still described the requests/httpx adapter with the **ADR-0012-rejected** binary mapping (`source: real or fallback`); the shipped code never emits `fallback`. | **Fixed** — rewrote to the shipped `real/high · real/medium · unavailable/none` mapping + ADR-0012 link. |
| 2 | `ROADMAP.md` #92 | P9 | #92 lacked a "shipped" marker despite the file annotating every other completed item. | **Fixed** — added "HTTP portion shipped in v0.7.2 (pandas/numpy pending v0.7.3)". |
| 3 | `primitives/python/http.py` docstring | P6 | Shipped docstring ended "Added in a later task." — stale planning scaffolding; the taggers are implemented in that same file. | **Fixed** — sentence removed. |
| 4 | `scripts/check_http_guarded_imports.py` comment | P6 | Comment referenced "see Task 1", meaningless to an external reader. | **Fixed** — made self-contained (explains the stdlib-`http` shadow). |
| 5 | `primitives/python/README.md` | P6 | The `from_cache` flag was listed as an equal cache-detection mechanism, but it's a no-op for stock requests/httpx (only caching-wrapper libs set it) and untested at the tagger level — overclaimed parity with the header heuristics. | **Fixed** — qualified: header detection is what fires for stock clients; `from_cache` honored if a wrapper sets it. |

Every finding is documentation/comment honesty drift — exactly what this pass
exists to catch (v0.7.0 caught stale version docs; v0.7.1 caught a zero-FP false
positive). No functional defect; the mechanical version-prose sweep was clean.

---

## v0.7.3 dogfood self-audit — 2026-07-19

Ran the `plumb-line-audit` method on plumb-line's own v0.7.3 diff (`c88204b..HEAD`),
lens on P6 (maturity honesty) and P9-style drift. **No product-code violations**;
two doc/test-discipline items, **both fixed before the tag** (commit `9574cbc`). The
adapter code, README, CHANGELOG, ROADMAP #92 closure, and version bump were all
consistent (mechanical version sweep clean).

| # | Location | Principle | Finding | Resolution |
| --- | --- | --- | --- | --- |
| 1 | `docs/adr/0013…md` §3 vs the combinator tests | P6 | ADR-0013 claimed *each* combinator's test asserts the result audits clean, but only `plumb_concat`/`plumb_concatenate` did — `plumb_merge`, both `plumb_derive`s, and `plumb_stack` tested propagation but never called `.audit()`. The ADR overstated the shipped test discipline. | **Fixed** — added `assert out.audit() == []` to the merge/derive/stack tests so the shipped tests match the ADR's promise (the stronger fix: fulfil the discipline, don't weaken the claim). |
| 2 | `PlumbDataFrame`/`PlumbArray` class docstrings | consistency (advisory) | The class docstring's "`.value` is the frame/array" contradicted `plumb_derive`'s own docstring (a reducing `fn` yields a Series/scalar) — an inconsistency introduced by the whole-branch-review Minor-2 docstring note. | **Fixed** — softened the class docstrings to "typically a frame/array; a reducing combinator may yield a narrower type." |

Both are honesty drift the dogfood exists to catch (v0.7.0: stale version docs;
v0.7.1: a zero-FP false positive; v0.7.2: ROADMAP describing an ADR-rejected design;
v0.7.3: an ADR promising test discipline the tests didn't fully carry).
