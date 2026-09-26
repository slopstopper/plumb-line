# ADR-0018: plumb-line's own source-truth layer and layer direction

**Status:** Accepted · 2026-09-25 (drafted for owner review, GH #434; amended after the PR #440 review; accepted by the owner before merge)

## Context

plumb-line holds itself to all nine principles (AGENTS.md), and every release
runs its audit skill over its own diff. Two of the principles need a
declaration to be checked. P1 — Source-truth layer asks which layer holds
the ground truth and what must never enter it. P2 — One-way layering asks
which way dependencies may point. The repository has never declared either
for itself, only one direction inside the primitive (ADR-0005: the wrapper
sits over the combinator). So the v0.11.1 and v0.11.2 dogfood runs could score
P1 and P2 only partially, and a later audit has nothing to measure a new
layer leak against (the v0.11.2 dogfood finding deferred as GH #434).

This ADR declares both, as they stand in the code on 2026-09-25, so an
audit has a rule to hold the code to. It invents no new structure: every
direction below, and each stated exception, is how the code already depends
(checked against the code on that date; the independent review of PR #440
found one runtime use the first draft missed, now listed).

## Decision

1. **Source truth is the definition of the law.** Two sets of
   files are the ground truth the rest of the repository is measured
   against:
   - **The envelope:** `primitives/SPEC.md` (the law and wire format, in
     prose) and the conformance tables under `primitives/conformance/`
     (`cases.json`, `http-cases.json`, `baseline-cases.json`, the
     executable definition). Neither the JS nor the Python implementation
     is source truth; each is measured against these files, and
     disagreement between the two is a defect in one of them, never a
     choice of which to trust.
   - **The method:** `reference/portable-principles.md` (the nine
     principles, their names and the principles revision). The skills
     teach it, and `scripts/check_report_format.py` reads names and revision
     from it rather than restating them.

   What must never enter these files: a value produced by running an
   implementation and pasted in without both implementations reproducing
   it (an expected lineage id, for example, is recorded only once both
   languages produce it), and prose that describes one implementation's
   behaviour instead of the law (the #401 step-id text was exactly this
   defect).

2. **One-way layering, top to bottom:**

   | Layer | May depend on | Must not depend on |
   | ----- | ------------- | ------------------ |
   | source truth (`primitives/SPEC.md`, `primitives/conformance/*.json`, `reference/portable-principles.md`) | nothing | anything below |
   | primitives (`primitives/js`, `primitives/python`) | source truth | adapters, scripts, skills, examples |
   | adapters (`adapters/`) | source truth; primitives in tests and docs, and at run time only through the one stated process boundary below | scripts, skills, examples |
   | consumers (`scripts/`, `skills/`, `examples/`, `evals/`, `portable/`, `action.yml`, `.claude-plugin/bundled/`, `primitives/conformance/*.mjs`, and docs such as `reference/fit-map.md`) | any layer above | each other only where stated below |

   Stated cross-layer uses:
   - **adapter → primitive, at run time, across a process boundary.**
     `adapters/sarif/run_checks.py` runs
     `node primitives/js/baseline-cli.mjs validate --json` for the Action's
     `baselines` capability (ADR-0016). It invokes the primitive's published
     CLI as a subprocess and reads its JSON; it imports nothing. Any other
     run-time use of the primitives by an adapter needs an amendment here.
   - **primitives' tests → consumers.** The primitives' own tests import
     `primitives/conformance/run-cases.mjs` (the shared interpreter of the
     source-truth tables) and read `reference/fit-map.md` (to run its
     snippets). Test code only; the published modules import neither.

   Consumers may depend on one another only in these stated ways:
   - the harness examples are scored by `scripts/`;
   - the skills name scripts as optional checks:
     `scripts/check_report_format.py` (audit, remediate, adopt) and
     `scripts/check_enforcement_manifest.py` (bootstrap);
   - `.claude-plugin/bundled/` is a byte-copy of `primitives/`, never
     edited in place.

## Maturity

- `current`: the bundle is a byte-copy of `primitives/`
  (`scripts/check-bundle-sync.mjs`, every PR).
- `current`: both implementations satisfy all three conformance tables.
- `current`, for `cases.json` only: every runner fails on a case field, case
  kind or table version it does not interpret
  (`primitives/conformance/run-cases.mjs` and the two Python suites; #369,
  #433).
- `planned`: the same three guards for `http-cases.json` and
  `baseline-cases.json`, whose four runners have none today (GH #441).
- `current`: the checker reads principle names and revision from
  `reference/portable-principles.md`.
- `planned`: a test that fails when a lower layer imports a higher one. As of
  this ADR the rule holds by inspection (2026-09-25). No published module
  under `primitives/` imports from `adapters/` or `scripts/`. No adapter
  runtime module imports the primitives: the lint rules recognise the
  primitive's module names as strings, which is how they detect
  `mark`/`derive` calls; the SARIF assembler links to `primitives/SPEC.md`;
  and `run_checks.py` runs the baseline CLI across the stated process
  boundary. Nothing enforces the rule yet. It becomes `current` when such a test
  lands, which this ADR proposes as the follow-up to acceptance.

## Consequences

- A dogfood audit can score P1 — Source-truth layer and P2 — One-way
  layering on this repository in full, instead of marking them partial.
- A change that makes an implementation the reference, for example by
  generating conformance expectations from one language's output and not
  checking them against the other, is a P1 violation by this ADR.
- An adapter that starts importing the primitive at run time, or calls it
  at run time other than through the stated baseline CLI, is a new
  dependency this ADR does not allow. It needs an amendment here before
  the import lands.
- ADR-0005's direction inside the primitive (wrapper over combinator) is
  unchanged and sits inside the primitives layer.

## Alternatives considered

- **Treat the JS implementation as the reference.** Rejected: it would make
  parity a matter of following one language, and the conformance tables
  exist so that neither language is.
- **Leave P1/P2 undeclared.** This is the state before this ADR. Every
  dogfood run then records the same partial coverage, which is a standing
  admission that two principles cannot be checked on the repository that
  teaches them.

## Amendments

- **2026-09-25 (v0.11.3 release harness, dogfood finding).** A third
  primitives-test use of a consumer, missing from the stated uses above:
  `primitives/js/conformance-runner.test.mjs` runs
  `primitives/conformance/report.mjs` as a subprocess, to pin that the
  self-certification verdict names its case table (#433). It is test code
  only, like the two uses already listed; the published modules still import
  nothing from the consumers layer. Recorded here rather than by editing the
  list, because this record is append-only.
- **2026-09-26 (#441).** The Maturity item "`planned`: the same three guards
  for `http-cases.json` and `baseline-cases.json`" is now `current`: each of
  the four runners fails on a case field, case kind or table version it does
  not interpret, and each guard is proven by a test that plants one. It
  brings a fourth primitives-test use of a consumer:
  `primitives/js/http.test.mjs` and
  `primitives/js/baseline.conformance.test.mjs` import
  `primitives/conformance/table-guards.mjs`, the guard helper, as the tests
  already import `run-cases.mjs`. Test code only; the published modules
  import nothing from it. The Python runners use
  `primitives/python/tests/case_table_guards.py`, which sits inside the
  primitives' own tests. Recorded here rather than by editing the lists,
  because this record is append-only.
