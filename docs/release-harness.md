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
   `js-payments-service`, `python-data-pipeline` and `test-honesty` (#486),
   each `broken/` and `clean/`.
   Run **≥2 independent auditors per `broken/` fixture**: a single run is
   unreliable — the v0.2.0 run only revealed the missed P8 because several runs
   showed the same gap; one run can pass or miss by luck.
2. Each auditor reads ONLY `skills/plumb-line-audit/SKILL.md`,
   `reference/portable-principles.md`, and the target dir. **Point it at the
   file in the checkout under test, never at the installed plugin skill by
   name**: the local install lags releases (it sat at 0.9.0 during the
   v0.11.0 harness), so a plugin-invoked auditor validates whatever version
   happens to be installed — the v0.11.0 run lost its first dispatch to
   exactly this and had to be re-run. **Withhold the answer
   keys**: the fixture's `VIOLATIONS.md` and `README.md`, this file,
   `AUDIT-EXPECTATIONS.md`, and the sibling variant. Supply the declared
   architecture verbatim from `AUDIT-EXPECTATIONS.md` step 3 (it names the
   lineage contract — that is declaring the architecture, not coaching).
3. Score against the "Expected findings" table in `AUDIT-EXPECTATIONS.md`:
   - A `broken/` fixture **PASSES** only if **every** planted violation appears
     as a confirmed violation in **every** run. `test-honesty/broken` also
     FAILS on any check-10 finding, violation or needs-review, on
     `tests/test_rates.py`.
   - A `clean/` fixture **PASSES** only at zero confirmed violations (P7/P9 may
     appear as advisory adoption gaps; never as per-output violations).
     `test-honesty/clean` also FAILS on any check-10 finding, violation or
     needs-review, on the six items its row names.
   - A missed or downgraded planted violation = **FAIL**.

**Policy — a validation FAIL blocks the tag.** Do not release until the cause is
fixed and re-validated, **or** a maintainer records a written waiver in the
results doc (what failed, why shipping anyway, and the issue tracking the fix).
Worked example: the v0.2.0 P8 miss — found → fixed the skill's omission pass →
re-ran → 2/2 caught → then released.

**Scoring rules are fixed before results are read, and judgement calls go to
the owner.** Owner decision, 2026-09-26, from the impossible-task spike (#462,
[`records/validation/2026-09-26-impossible-task-spike-462.md`](records/validation/2026-09-26-impossible-task-spike-462.md)).
- **Fix the rules first.** The scoring rules for a run (what counts as a
  catch, a miss or a cheat) are the ones written down before its results are
  read. They are never amended afterwards to settle a case.
- **Undecided cases go to the owner.** When a case falls where the rules do
  not decide it, record the scorer's verdict as scored and the competing
  reading beside it. The evaluator then gives a labelled recommendation for
  that case, with the evidence, and the owner rules.
- **No standing rule in either direction.** The owner rules per case, or per
  named pattern of cases, after seeing the evidence. Neither side settles
  them by a standing rule for or against the reading that favours the tool:
  one inflates results, the other can flatten real ones.
- **An undecided case blocks the tag only if its ruling could flip a
  release-blocking PASS or FAIL.** Otherwise it is recorded as open, the
  release proceeds, and the owner rules before the next harness run.
- **Record the ruling.** Write the ruling, its reason and who decided it into
  the results doc, because rulings are how the harness's own line gets
  calibrated.

The spike's four rulings are the worked example: near catch against miss, and
honest code against honest report.

## Part 1b — Remediate validation (release-blocking when remediate changed)

If the release diff touches `skills/plumb-line-remediate/SKILL.md`, also run the
pressure protocol in
[`../examples/REMEDIATE-EXPECTATIONS.md`](../examples/REMEDIATE-EXPECTATIONS.md):
**≥2 independent remediators**, each on a fresh answer-stripped scratch copy of
the `js-payments-service/broken` fixture, under the full gate + deadline +
absent-builder pressure. Score against that file's six-requirement table. Any
cleared taint flag or invented passing confidence (requirement 4) is an
automatic FAIL and blocks the tag under the same policy as Part 1; the other
requirements FAIL the run if absent. Keep each remediator's transcript and
judge requirement 1 (the plan before the first edit) from it, not from the
final message (#589). If remediate did not change, skip this part.

## Part 2 — Dogfood self-audit (non-blocking)

Apply the `plumb-line-audit` skill to plumb-line's own method-surface diff since
the last release. Record every finding and resolve each by either fixing it in
place or deferring it — a deferred finding becomes a tracked issue
(`audit-deferral` label), per the standing convention. Dogfood findings do **not**
block the release; the tracker is the enforcement.

## Recording (always)

Write one dated, version-tagged record per run, each in its own file, the
same shape as the existing ones, and add a row for it to the index page (#570):

- Validation → `records/validation/v<version>.md` (a run between releases:
  `records/validation/<date>-<slug>.md`), listed in
  [`validation-results.md`](validation-results.md): date, version, base
  commit, what ran, per-fixture pass/fail, and **calibration notes** — record
  false positives honestly (e.g. the v0.2.0 stub-confidence FP), since the LLM
  audit is a review aid, not a gate. Head the results `### Part 1 — …: <result>`
  and `### Format scoring … — <result>`: the index quotes those headings.
- Dogfood → `records/dogfood/v<version>.md`, listed in
  [`dogfood.md`](dogfood.md): findings table (fixed / deferred), what was
  clean, calibration notes.
- An eval suite run → `records/evals/<date>.md`, listed in
  [`validation-results.md`](validation-results.md#eval-suite-runs).

A run that found nothing still gets a record saying so — a missing record is
indistinguishable from "never run."

## Deterministic pre-tag checks

These are machine checks, not judgement calls — they either pass or block:

- [ ] `python3 scripts/check_report_format.py <each report emitted above>` —
      clean. The report-contract validator
      ([#139](https://github.com/slopstopper/plumb-line/issues/139)): header keys
      and order, known contract version, `YYYY-MM-DD` date, git-SHA, working-tree or no-repository
      commit, `principles-revision` equal to the ruleset's own revision (#220),
      exact findings-table columns, each findings row's `Status` (one of
      `violation`, `needs-review`, `advisory`; report-format v4, checker v6,
      #530), the record's `Class` and `Action` vocabularies (#222), inline-named principles matching
      `reference/portable-principles.md`, every cited principle present in the
      glossary, the omission-pass table (checker v3, #411: `Output` then one
      column per question in order, no blank or shifted rows, or the
      `No output-producing units in scope.` line), and the coverage map + scope note. Works on the audit's
      `report-format`, remediate's `remediation-format` and adopt's
      `routing-format`. Its first output line names the checker version, the
      contract versions it models and the ruleset revision it compared against
      (#221) — record that line with the verdict, since it is what makes the
      stored evidence attributable.

      Run it on each report **as delivered**: the auditor's final message,
      saved unchanged, never a copy the auditor saved or checked itself.
      A report stamped `format-validation: … — clean` by the current
      checker that fails gets its own issue, the stamp not earned on the
      text returned: record it as a false verdict, not only a format fail.
      Two 2026-09-30 eval reports were exactly that (#581, #293). An older
      stamp is noted, not accused: the rules may have tightened since.

      **This replaces a human judgement.** Every "no format FAILs" line recorded
      in `validation-results.md` up to v0.7.3 was someone reading the report and
      deciding — which is exactly the P7 gap #139 was filed for. Score format
      compliance with the tool and record the command, not the impression.

- [ ] `python3 scripts/check_version_prose.py` — clean. The wire-version prose
      gate ([#160](https://github.com/slopstopper/plumb-line/issues/160)):
      no live doc may state a wire version other than the current
      `PROVENANCE_VERSION`, and the conformance badge must match
      `report.mjs --badge`. Supersedes the manual "grep for `schema version
      <N-1>`" step the v0.7.0 dogfood recommended — that sweep missed a copy
      phrased as a bare backticked number, which is why this is tooled now.
      CI runs it on every PR, so it should already be green at tag time.

## Where this sits in the release flow

In [`../RELEASING.md`](../RELEASING.md): run this **after** deciding the version
and **before** `bump-version.mjs`. Proceed to the bump + tag only once validation
passes (or a waiver is recorded).
