# Audit harness — blind protocol + expected findings

The `plumb-line-audit` skill is an LLM behavior, not deterministic code, so it
cannot be unit-tested the way the adapters can. This file is its **regression
harness**: a fixed protocol plus the expected result per fixture, so a future run
(by a human or an agent) can be scored repeatably after any change to the skill.

The deterministic companion — `test_fixture_integrity.py` — locks the fixtures
themselves so the answer keys below stay true to the code. Run both: the pytest
file on every change, this protocol whenever `skills/plumb-line-audit/SKILL.md`
changes.

This protocol is also a release gate: [`../docs/release-harness.md`](../docs/release-harness.md)
runs it before tagging any release that touches the method surface, and a missed
planted violation blocks the release.

## Protocol (run one auditor per variant)

1. The auditor reads ONLY `skills/plumb-line-audit/SKILL.md` and
   `reference/portable-principles.md`, then the target directory.
2. **Withhold the answer keys.** The auditor must NOT read `VIOLATIONS.md` or
   `README.md` for the fixture under audit — both list the planted violations.
   Reading either invalidates the run.

   **Strip the inline annotations too.** The `js-payments-service/broken`
   sources carry comments naming the planted violation *and its principle
   number* (`// VIOLATION P2: upward import …`), so an auditor reading the
   fixture is handed the answer key even with both files withheld. Run the
   auditor against a scratch copy outside the repo with the key files deleted
   and every line matching `violation` **case-insensitively** removed — the
   same treatment `REMEDIATE-EXPECTATIONS.md` step 1 applies. Verify the copy is
   clean (`grep -ri violation <scratch>` returns nothing) before dispatching:
   until v0.8.0 this step did not exist, and the JS `broken/` runs recorded
   through v0.7.3 were scored on an annotated fixture.
3. Supply the declared architecture the way a real project owner would (the
   auditor cannot infer a project's own rules): one-way direction
   `ui → services → engine → data` (non-adjacent downward skips allowed);
   priors come from `config/`; **the service layer is the lineage-bearing
   output** — its result records a `lineage` of the inputs needed to reproduce
   it (source identity, record count, field names, config/version); outputs also
   carry provenance + confidence and propagate the priors version. (Naming the
   lineage contract is declaring the architecture, not coaching toward a
   specific finding — the auditor still has to notice whether each output
   honours it.)
4. Use an identical, plain prompt for every variant — do not coach the auditor
   toward the expected findings. The skill must perform on a plain invocation.
5. The report MUST open with the `report-format: v3` header block (scope,
   `principles-revision`, date, commit) and MUST include the coverage map — every
   in-scope file marked `read` / `partial` / `not-read`, with an honest
   denominator. A missing or malformed header, or a report that claims or implies
   full coverage without the map, is a **format FAIL**, scored independently of
   finding accuracy — a report that can't be reproduced fails even if every
   finding is correct.

## Expected findings

### `broken/` — exactly the planted set must appear as VIOLATIONS

| Fixture              | Must flag as violations                                      | Principle |
| -------------------- | ------------------------------------------------------------ | --------- |
| js-payments-service  | `data/rates.js` upward import                                | P2        |
|                      | `engine/pricing.js` hardcoded `FEE`                          | P5        |
|                      | `services/gateway.js` response missing provenance/confidence | P3        |
| python-data-pipeline | `data/schema.py` upward import                               | P2        |
|                      | `engine/aggregate.py` hardcoded `SIGNAL_THRESHOLD`           | P5        |
|                      | `services/source.py` missing `lineage`                       | P8        |

Scoring: **PASS** only if all three planted violations for a fixture appear as
confirmed violations. The P8 row is the regression this harness exists to guard —
a missing-lineage omission caught only by the skill's omission pass + the
"declared adoption" calibration. Extra advisory/needs-review items are acceptable;
a _missed_ planted violation or a planted violation downgraded to advisory is a
FAIL.

### `clean/` — zero violations of adopted principles

| Fixture              | Expected               | Allowed (advisory only)                                                                    |
| -------------------- | ---------------------- | ------------------------------------------------------------------------------------------ |
| js-payments-service  | 0 confirmed violations | P7 (no contracts), P9 (no baseline) as adoption gaps; spine stub-rejection as needs-review |
| python-data-pipeline | 0 confirmed violations | P7, P9 as adoption gaps; binary engine confidence as needs-review                          |

Scoring: **PASS** if the auditor reports zero confirmed _violations_. P7/P9
absences must appear (if at all) as advisory adoption gaps, never as per-output
violations — the fixtures deliberately do not adopt contracts or baselines (see
each fixture's README "Scope" section). A confirmed violation on `clean/` is a
FAIL — either the skill over-claimed or the fixture regressed.

## History

- 2026-06-28: first run found the python `broken/` P8 (missing-lineage) omission
  was NOT caught (false negative) and both `clean/` variants drew spurious P7
  contract violations. Fixed by adding the omission pass + declared-adoption
  calibration to the skill, and by propagating `weightsVersion` end-to-end (JS)
  and lifting stub confidence to config (Python) so `clean/` is genuinely clean.
