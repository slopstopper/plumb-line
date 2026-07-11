# Changelog

All notable changes to plumb-line are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

The version numbers below track the **packages and plugin**. The envelope wire
format is versioned separately as `PROVENANCE_VERSION` (currently `2`).

## [Unreleased]

_Nothing yet._

## [0.7.0] — 2026-07-11

### Changed
- **Envelope wire format bumped to `PROVENANCE_VERSION` 2** (breaking) — the
  first wire bump since v1, batching three schema changes so the version moves
  exactly once ([ADR-0010](docs/adr/0010-wire-v2-schema-batch.md)):
  - **Content-addressed lineage step ids** — `combineProvenance` /
    `combine_provenance` no longer renumber the lineage `step-N`; each step now
    carries a `sha256:` id derived from its own fields plus its input steps' ids
    (Merkle). Ids are stable across recombination and dedupe identical
    derivations, replacing the per-combine renumbering that made a step's id
    depend on what it was later combined with
    ([#52](https://github.com/effythealien/plumb-line/issues/52)).
  - **`inferred` source rung** — the source ladder gains a seat for
    LLM/agent-produced values: `unavailable < mock < inferred < fallback <
    semiReal < derived < real`. Placed just above `mock`, so `combine` treats an
    inferred value as suspect until evidenced
    ([#116](https://github.com/effythealien/plumb-line/issues/116)).

### Added
- **Per-envelope `provenanceVersion`** — every envelope produced by
  `makeMeta` / `make_meta` (and therefore `combine`) now embeds the schema
  version. The checkers validate it with an asymmetric read policy: an
  unknown-newer version passes with a `version-future:` advisory, an
  absent/older one is accepted but flagged `version-legacy:`, and the current
  version is clean — forgiving forward, honest backward
  ([#93](https://github.com/effythealien/plumb-line/issues/93)).
- **Bundled runtime primitive** — the zero-dependency provenance modules are
  now vendored into the plugin (`.claude-plugin/bundled/primitives/`), so
  `plumb-line-bootstrap` can scaffold `mark`/`derive` into a host project with
  no separate `npm`/`pip` install. A CI drift check keeps the bundle
  byte-identical to `primitives/` and runs it against the same conformance
  suite ([#99](https://github.com/effythealien/plumb-line/issues/99)).

## [0.6.0] — 2026-07-05

### Added
- **Adopt-the-primitive offer slice** — the two skill halves of ROADMAP #6 that
  connect the plugin to the runtime library. `plumb-line-method` now names
  `plumb-line-provenance` (with the three-line `mark`/`derive` example and the
  npm/pip install) whenever a walk covers P3 or P8 — mention and suggest only,
  the skill still takes no actions
  ([#106](https://github.com/effythealien/plumb-line/issues/106)).
  `plumb-line-bootstrap` gains Step 4b: after enforcement install, one explicit
  opt-in offer to scaffold `mark`/`derive` at the call sites the interview
  surfaced (Q4 downstream values, Q8 lineage outputs), teaching the pattern at
  the first site and wiring an audits-clean test into the pre-commit gate;
  declining leaves the project untouched, and unscaffolded sites are recorded
  as `planned`
  ([#107](https://github.com/effythealien/plumb-line/issues/107)).
- **Provenance-lint injection path** (D7 deferral) — both linters can now extend
  coverage to wrapper/re-export modules without patching source: the ESLint rule
  gains `modules` (extra import sources counted as the primitive) and `tracked`
  (wrapper-name → role mapping, schema-validated) options; the Python checker
  gains matching `extra_modules` / `extra_tracked` parameters (unknown roles
  raise `ValueError` — fail loud, not silently-missing coverage). Both are
  additive: built-in coverage cannot be configured away
  ([#29](https://github.com/effythealien/plumb-line/issues/29)).
- **`plumb-line-remediate` skill** — the fourth skill closes the find→fix loop:
  it consumes an audit report (`report-format: v1`+), classifies every finding
  mechanical vs. judgment before touching anything, applies fixes one finding at
  a time with a diff shown per finding, and ends every run with a
  `remediation-format: v1` record (the remediation's own lineage). Judgment
  fixes with no builder present take the **conservative floor** — the weakest
  honest claim, never an invented middle confidence — and are flagged for
  review. The honesty guardrail from ROADMAP #11 is enforced: a fix may never
  make code less honest (clear a taint flag, invent a passing confidence,
  delete a null-result branch, silently update a baseline); when only a
  dishonest edit would satisfy a finding or gate, it is recorded as `blocked`
  with the honest paths out. Validated RED→GREEN against a new pressure
  harness, `examples/REMEDIATE-EXPECTATIONS.md`, now part of the release gate
  ([#57](https://github.com/effythealien/plumb-line/issues/57)).

### Fixed
- **`python-data-pipeline/clean` fixture parity** — the v0.6.0 release harness
  caught the Python clean fixture carrying `weights_version` only inside
  `display_text`, while the JS clean fixture propagates it structurally: a
  blind auditor correctly flagged it as a violation of the declared
  propagate-the-priors-version rule. The fixture now returns `weights_version`
  as a structured key, a fixture-integrity lock pins it, and the blind re-run
  passed with 0 confirmed violations (see `docs/validation-results.md`, 0.6.0
  record).
- **Dogfood fixes from the v0.6.0 self-audit** — README skill count in Status
  (merge artifact), method skill no longer says taint is "impossible to clear"
  (tamper-*evident*, not tamper-proof — now "no API exists to clear it"), the
  lint README states the JS-vs-Python module-matching divergence instead of
  claiming "same semantics" (alignment deferred → #138), and the remediate
  harness history now records the commit SHA + principles revision per entry.
  P7 validator for report/remediation formats deferred → #139. See
  `docs/dogfood.md`, v0.6.0 section.

## [0.5.1] — 2026-07-03

### Added
- **Audit remediation handoff** (`plumb-line-audit`) — after printing the report,
  the auditor now offers a read-only next step: hand the findings to a planning
  skill (superpowers `writing-plans` / plan mode) for a fix-plan, and, when a
  finding exposes a provenance/lineage/boundary gap, suggest `plumb-line-bootstrap`
  to wire enforcement. It applies nothing itself — mechanical fixing stays the
  planned `plumb-line-remediate` skill
  ([#88](https://github.com/effythealien/plumb-line/issues/88)).
- **Onboarding + three-skill cross-links** (`plumb-line-method`) — method now
  names `plumb-line-bootstrap` as the explicit next step, maps all three skills
  (method → bootstrap → audit), and documents the first-run flow — including that
  a marketplace plugin cannot auto-execute a skill on install, so `/method` does
  not auto-run. Bootstrap and audit gain reciprocal cross-links
  ([#89](https://github.com/effythealien/plumb-line/issues/89)).

These two themes were scoped to v0.5.0 but shipped narrower; v0.5.1 completes the
"audit you can act on" theme. See [ROADMAP.md](ROADMAP.md).

## [0.5.0] — 2026-07-03

### Added
- **Developer Certificate of Origin** — contributions are now certified under
  the [DCO](DCO) 1.1. A CI check (`.github/workflows/dco.yml`) requires a
  `Signed-off-by` trailer on every commit, and a bundled `prepare-commit-msg`
  hook (`git config core.hooksPath .githooks`) adds it automatically. Satisfies
  the OpenSSF Best Practices **silver** `dco` criterion.
- **Project governance** — `GOVERNANCE.md` documents the decision-making model,
  roles and responsibilities, and access/continuity (including the
  no-stored-secrets, OIDC-based release design), toward the OpenSSF Best
  Practices **silver** badge.
- **Enforced lint** — ESLint (JS) and Ruff (Python) now run as a CI gate;
  `npm run lint` in each JS package, `ruff check .` for Python.
- **Coverage gate** — the test suites now measure statement coverage and fail
  under 80% (currently ~96–99% on the primitives, ~96–99% on the adapters).
  Process-entry CLI glue is excluded (it is exercised by the spawn-based hook
  tests, not in-process).
- **Silver-badge gap analysis** — `docs/ossf-silver-gap-analysis.md` maps the
  project against every silver criterion with form-ready answers.

### Changed
- **Audit is now honest about its own coverage** (`report-format: v2 → v3`):
  `plumb-line-audit` emits an up-front **traversal plan** and a required
  **coverage map** — every in-scope file marked `read` / `partial` / `not-read`,
  with a count and an explicit no-completeness caveat — so a report can no longer
  imply it read the whole tree when it only sampled
  ([#87](https://github.com/effythealien/plumb-line/issues/87)). The
  `plumb-line-bootstrap` header moves to `v3` in lockstep; `principles-revision`
  stays `1` (no principle's meaning, scope, or vocabulary changed).

### Fixed
- **Audit spine calibration no longer over-claims on a deliberate stub.** An
  always-accept / always-success stub (e.g. a `submitPayment` that can only
  return `accepted: true`) on a layer that neither declares nor practices
  rejection is now reported as a `needs-review` advisory adoption gap, not a
  confirmed spine violation — matching the clean-fixture handling of P7/P9 and
  the `examples/AUDIT-EXPECTATIONS.md` answer key
  ([#101](https://github.com/effythealien/plumb-line/issues/101)).

## [0.4.1] — 2026-07-02

### Changed
- **Audit report is now legible and deterministic** (`report-format: v1 → v2`):
  a principle glossary + inline principle names (no bare `P#`) opens every report
  ([#83](https://github.com/effythealien/plumb-line/issues/83)); the findings
  section is now a single canonical table with `Path`/`Line`/`Function` split out
  and a `Suggested Fix` column, replacing the run-to-run prose/table variance
  ([#84](https://github.com/effythealien/plumb-line/issues/84)); and the
  `plumb-line-audit.md` artifact follows an **always-offer, never-auto-write**
  contract — the report always prints to chat, the file is written only on an
  explicit yes ([#85](https://github.com/effythealien/plumb-line/issues/85)). The
  bootstrap report header moves to `v2` in lockstep.
- **README** leads with the marketplace plugin install (least-friction on-ramp)
  ([#86](https://github.com/effythealien/plumb-line/issues/86)).

### Fixed
- **`auditMeta` / `audit_meta` is total and parity-clean on non-object input.**
  Python previously raised `AttributeError` on a falsy-but-not-`None` scalar
  (`0`, `''`, `False`); both languages now return `["missing meta"]` for any
  non-plain-object input (null/None, falsy scalars, strings, numbers, arrays)
  while an empty object/dict still audits clean — restoring SPEC §5 totality and
  cross-language parity. Pinned by new conformance cases.
  ([#80](https://github.com/effythealien/plumb-line/issues/80))

## [0.4.0] — 2026-07-01

### Added
- **`validateEnvelope` / `validate_envelope` — a structural field-presence
  checker** (P7), the complement to `auditMeta`. The audit checks logical
  consistency among *present* fields and tolerates absence as "unknown" (SPEC
  §2), so a structurally empty `{}` audits clean; the new validator checks that
  the four required fields (`source`, `confidence`, `derivedFromMock`, `lineage`)
  are present and well-typed. Same list-of-issue-strings shape, equally total
  (`null`/non-object yield a list, never throw). Specified in SPEC §5a; pinned by
  a `validate` case kind in the conformance suite (now run by `report.mjs` too)
  and verified in both languages. The envelope wire format is unchanged —
  `PROVENANCE_VERSION` stays `1`. Promotes the README maturity row `planned` →
  `current`. [#27](https://github.com/effythealien/plumb-line/issues/27)

### Changed
- **Audit and bootstrap reports now carry a reproducible header** (P7 + P8). Both
  `plumb-line-audit` and `plumb-line-bootstrap` reports MUST open with a
  `report-format: v1` header block — `scope`, `principles-revision`, `date`, and
  `commit` — so a stored report names exactly what was audited, against which
  rules, at which commit. `reference/portable-principles.md` gains a
  **Principles revision** stamp (starting at `1`) for the header to cite, and the
  audit harness protocol (`examples/AUDIT-EXPECTATIONS.md`) now scores a
  missing/malformed header as a format failure independent of finding accuracy.
  [#28](https://github.com/effythealien/plumb-line/issues/28)

### Documentation
- **`basis` is now documented as the operation-label convention** (P8). Lineage
  records each input's trust state but not the transformation `fn`, so two
  `derive` calls with identical inputs but different transforms produce identical
  lineage. `derive` callers who need the transform recorded SHOULD pass `basis` as
  a short, stable operation label (e.g. `"pricing.applyFx@v3"`); it stays
  advisory (the law never writes or validates it, and its absence is never an
  audit finding). Capturing `fn` identity itself remains out of scope for envelope
  schema version 1. Documented in SPEC §4, `primitives/README.md`, and the
  `derive` docstrings. [#26](https://github.com/effythealien/plumb-line/issues/26)

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

[Unreleased]: https://github.com/effythealien/plumb-line/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/effythealien/plumb-line/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/effythealien/plumb-line/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/effythealien/plumb-line/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/effythealien/plumb-line/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/effythealien/plumb-line/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/effythealien/plumb-line/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/effythealien/plumb-line/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/effythealien/plumb-line/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/effythealien/plumb-line/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/effythealien/plumb-line/releases/tag/v0.1.0
