# Release harness — run before tagging a method-surface release

The one-shot procedure to run before cutting a release that changes the **method
surface**. It re-proves that plumb-line's own discipline still holds as the code
evolves, in two parts:

- **Blind validation** — the auditor still catches the planted violations in
  `examples/` (the method working on known-bad fixtures).
- **Dogfood self-audit** — the auditor catches smells in plumb-line's own new
  code (the method working on our own diff).

Both are LLM behaviors, so they live here as a runbook rather than in CI. The
*deterministic* parts — the `examples/` fixture tests, conformance parity, and
fixture integrity — already gate every PR in `.github/workflows/ci.yml`; this
runbook covers only the non-deterministic layer.

## When to run

Run if the release diff since the last tag touches the method surface:

```sh
git diff --name-only "$(git describe --tags --abbrev=0)"..HEAD \
  | grep -Eq '^(skills/|reference/portable-principles\.md|primitives/|adapters/)' \
  && echo "method-surface changed → run the harness" \
  || echo "docs/chore only → skip the harness"
```

A docs/chore-only release skips it. Everything else runs both parts below.

## Part 1 — Blind validation (release-blocking)

Follow the blind protocol in
[`../examples/AUDIT-EXPECTATIONS.md`](../examples/AUDIT-EXPECTATIONS.md):

1. Dispatch read-only auditors, **one per fixture variant** —
   `js-payments-service` and `python-data-pipeline`, each `broken/` and `clean/`.
   Run **≥2 independent auditors per `broken/` fixture**: a single run is
   unreliable — the v0.2.0 run only revealed the missed P8 because several runs
   showed the same gap; one run can pass or miss by luck.
2. Each auditor reads ONLY `skills/plumb-line-audit/SKILL.md`,
   `reference/portable-principles.md`, and the target dir. **Withhold the answer
   keys**: the fixture's `VIOLATIONS.md` and `README.md`, this file,
   `AUDIT-EXPECTATIONS.md`, and the sibling variant. Supply the declared
   architecture verbatim from `AUDIT-EXPECTATIONS.md` step 3 (it names the
   lineage contract — that is declaring the architecture, not coaching).
3. Score against the "Expected findings" table in `AUDIT-EXPECTATIONS.md`:
   - A `broken/` fixture **PASSES** only if **every** planted violation appears
     as a confirmed violation in **every** run.
   - A `clean/` fixture **PASSES** only at zero confirmed violations (P7/P9 may
     appear as advisory adoption gaps; never as per-output violations).
   - A missed or downgraded planted violation = **FAIL**.

**Policy — a validation FAIL blocks the tag.** Do not release until the cause is
fixed and re-validated, **or** a maintainer records a written waiver in the
results doc (what failed, why shipping anyway, and the issue tracking the fix).
Worked example: the v0.2.0 P8 miss — found → fixed the skill's omission pass →
re-ran → 2/2 caught → then released.

## Part 2 — Dogfood self-audit (non-blocking)

Apply the `plumb-line-audit` skill to plumb-line's own method-surface diff since
the last release. Record every finding and resolve each by either fixing it in
place or deferring it — a deferred finding becomes a tracked issue
(`audit-deferral` label), per the standing convention. Dogfood findings do **not**
block the release; the tracker is the enforcement.

## Recording (always)

Append a dated, version-tagged section — same shape as the existing v0.2.0 ones:

- Validation → [`validation-results.md`](validation-results.md): date, version,
  base commit, what ran, per-fixture pass/fail, and **calibration notes** —
  record false positives honestly (e.g. the v0.2.0 stub-confidence FP), since the
  LLM audit is a review aid, not a gate.
- Dogfood → [`dogfood.md`](dogfood.md): findings table (fixed / deferred), what
  was clean, calibration notes.

A run that found nothing still gets a recorded section saying so — a missing
section is indistinguishable from "never run."

## Where this sits in the release flow

In [`../RELEASING.md`](../RELEASING.md): run this **after** deciding the version
and **before** `bump-version.mjs`. Proceed to the bump + tag only once validation
passes (or a waiver is recorded).
