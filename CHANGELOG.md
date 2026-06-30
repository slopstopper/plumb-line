# Changelog

All notable changes to plumb-line are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

The version numbers below track the **packages and plugin**. The envelope wire
format is versioned separately as `PROVENANCE_VERSION` (currently `1`).

## [Unreleased]

_Nothing yet._

## [0.3.1] — 2026-07-01

### Changed
- **SPEC §1 versioning gains a self-contradiction carve-out.** Correcting a
  combination result that another normative section of the SPEC already flags as
  inconsistent (the zero-input case below: §3 said `derived`, §5 said that's
  unreproducible) is now defined as a *conformance fix*, not a breaking change,
  and MUST NOT bump `PROVENANCE_VERSION` — provided it's recorded (CHANGELOG +
  ADR) and pinned by a conformance case. `PROVENANCE_VERSION` stays `1`. See
  [ADR-0008](docs/adr/0008-zero-input-conformance-fix-no-wire-bump.md). The SPEC
  header also drops the "(stable — no breaking changes planned)" parenthetical (a
  P6 maturity over-claim).

### Fixed
- **Zero-input `combineProvenance()` no longer contradicts the audit** (P8). A
  value combined from no inputs now reports `source: "unavailable"` instead of
  `"derived"`, so it no longer trips `auditMeta`'s *unreproducible: derived value
  has no lineage* check (SPEC §3 vs §5). `SPEC.md` §3 updated; a combine case and
  an audit case pin the resolution in the conformance suite.
  [#25](https://github.com/effythealien/plumb-line/issues/25)
- **Lineage step IDs are now concurrency-safe** (P8). The module-level step
  counter is gone; each `combineProvenance` renumbers its **entire output
  lineage** from a call-local counter, so step IDs can't collide or become
  non-monotonic under worker threads, async event loops, or parallel test
  runners — and stay **unique-within-output** (SPEC §4) for every input shape,
  including combining two independently-built envelopes that each start at
  `step-1`. IDs are now a pure function of output structure, not creation order.
  `__resetStepCounter` / `reset_step_counter` are now deprecated no-ops, kept
  for import compatibility.
  [#23](https://github.com/effythealien/plumb-line/issues/23)

## [0.3.0] — 2026-06-30

### Added
- **Conformance coverage** for two checker conditions previously defined only in
  SPEC prose: *dropped taint* (§5 condition 5) and *unreproducible* (§5
  condition 6), plus null-envelope and empty-envelope cases. A new-language port
  can no longer pass the full suite while omitting these conditions.
- Skill **stop-and-report guards**: `plumb-line-audit`, `plumb-line-bootstrap`,
  and `plumb-line-method` now halt instead of falling back to training-data
  recollection when `reference/portable-principles.md` is unreadable.

### Changed
- **Python lint adapter `check()` is now self-describing** — every issue dict
  (including parse errors) carries `filename`, and `check()` accepts a
  `clean_sources` override mirroring the JS rule's `opts.sources`. **Breaking
  for the Python adapter:** callers doing exact-dict equality on `check()`
  output must account for the new `filename` key.
- `primitives/SPEC.md` status `stable` → `current` (P6 vocabulary); the
  schema-version stability claim is now a parenthetical.
- `reset_step_counter` removed from `primitives/python` `__all__` (still
  importable directly for test suites); marked test-only in JS and Python.

### Fixed
- **`plumb-line-audit` omission pass** now reliably catches missing-lineage (P8):
  the required table must give `lineage` its own column, distinct from
  `provenance`/`confidence`, and a present provenance string no longer counts as
  satisfying lineage. The `AUDIT-EXPECTATIONS.md` protocol brief now names the
  lineage contract. Found by the v0.2.0 validation re-run (3/3 blind runs missed
  the planted P8 before; 2/2 catch it after). [#31](https://github.com/effythealien/plumb-line/issues/31)

### Notes
- Source: the **v0.2.0 self-audit** (dogfooding pass, see `docs/dogfood.md`) and
  the **v0.2.0 validation re-run** (see `docs/validation-results.md`).
  Eight self-audit findings fixed there; seven deferred and tracked as issues
  [#23](https://github.com/effythealien/plumb-line/issues/23)–[#29](https://github.com/effythealien/plumb-line/issues/29).

## [0.2.0] — 2026-06-29

### Added
- Optional **numeric confidence** (`confidenceScore`, `[0,1]`) and a
  **weakest-source** field on the provenance envelope; two new audit checks
  (numeric over-claiming, source over-claim).
- A versioned **specification** (`primitives/SPEC.md`, envelope schema version 1)
  and a single cross-language **conformance suite** with a report/badge tool.
- **npm + PyPI packaging** — the primitive is published as `plumb-line-provenance`.
- A static **`no-provenance-bypass` lint** (ESLint rule for JS, stdlib-`ast`
  checker for Python) that flags provenance-bypass patterns at review time.
- **GitHub Actions CI** running the JS and Python suites on push and PR.
- **Feedback channels** — a GitHub issue form and a private (Formspree-backed)
  form served via GitHub Pages.

### Changed
- **Relicensed from MIT to Apache-2.0** (added a `NOTICE` file).
- README repositioned to lead with the run-time primitive.

### Notes
- Envelope wire format unchanged: `PROVENANCE_VERSION` stays `1`.

## [0.1.0] — 2026-06-28

### Added
- Initial release: the three Claude Code skills (`method`, `bootstrap`,
  `audit`), the run-time provenance primitive with JS/Python parity, and
  enforcement adapters (ESLint / import-linter boundaries, git hooks) for
  JavaScript/TypeScript and Python.

[Unreleased]: https://github.com/effythealien/plumb-line/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/effythealien/plumb-line/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/effythealien/plumb-line/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/effythealien/plumb-line/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/effythealien/plumb-line/releases/tag/v0.1.0
