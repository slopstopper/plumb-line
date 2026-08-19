# OpenSSF Scorecard — accepted residuals

Why each non-perfect check is not being fixed, and what would change that
([#77](https://github.com/slopstopper/plumb-line/issues/77)).

Kept deliberately short. A justification is a maintenance burden: the longer this
file is, the more of it is quietly wrong at any moment. Re-check the numbers
rather than trusting the prose.

```bash
curl -s https://api.scorecard.dev/projects/github.com/slopstopper/plumb-line
```

**Last checked:** 2026-08-11 · **Overall 7.0/10** · no residual is an exploitable
vulnerability in shipped code (both published packages declare zero runtime
dependencies).

## Residuals

| Check | Score | Why not fixed | Changes when |
| --- | --- | --- | --- |
| Vulnerabilities | 8 | Two `brace-expansion` DoS advisories — **patched** to 5.0.9 in this change | Next scan re-reads the lockfiles |
| Pinned-Dependencies | 9 | `npm install -g npm@11.18.0` in `release.yml`; a `-g` install can't be hash-pinned, and removing it breaks trusted publishing | npm supports a pinnable install |
| Contributors | 6 | Two contributing orgs detected; full marks need ≥3 | A third org contributes |
| Branch-Protection | 5 | Ruleset requires 0 approvals, classic requires 1, `enforce_admins` is false — merges land unapproved | PR review becomes part of the workflow (see below) |
| Maintained | 0 | Repo created 2026-06-28, inside the 90-day window | Re-evaluate after 2026-09-26 — it then scores on activity, not age |
| Code-Review | 0 | 0 of 9 changesets approved | Same as Branch-Protection |
| Fuzzing | 0 | No OSS-Fuzz integration; out of proportion for this library. JS property tests exist but don't count | Someone takes on OSS-Fuzz |
| Signed-Releases | −1 | 13 releases exist but carry no assets, so the check is uncounted. Registry trusted publishing already attests provenance | Assets are attached — this is a decline, not an inability |

**Resolved and observed** (scan of 2026-08-18): **CII-Best-Practices 0 → 7,
"badge detected: Silver"** — the 2026-08-11 URL fix took effect on the next
scan, exactly as the row above predicted, and entry 13453 has since completed
the silver questionnaire ([#217](https://github.com/slopstopper/plumb-line/issues/217)
closes on this observation). **Vulnerabilities → 9** in the same scan. Neither
is asserted from memory; re-run the curl above to check.

## Branch-Protection and Code-Review

Both scores come from the same fact: **changesets merge without approvals.**

Two systems are live on `main` at once. The ruleset `protect-main` requires 0
approvals with code-owner review on; classic protection requires 1 with stale
dismissal on and four required checks. `enforce_admins` is `false`. The precise
interaction that lets a PR merge while showing `REVIEW_REQUIRED` is **not
established** — earlier drafts of this file asserted three different mechanisms
and all three were wrong, so it is left as an open question rather than a fourth
guess.

The org has two members, but they work on separate projects — plumb-line is not
jointly reviewed. That is a workflow fact, not a security decision, and neither
score will drift upward on its own.

If review is ever adopted, four things need changing together: the ruleset's
approval count and stale-dismissal, classic `enforce_admins`, and
`.github/CODEOWNERS` — which currently lists one owner for every path, so nobody
else's approval would satisfy code-owner review.

Note Scorecard is *over*-generous here: it credits admin enforcement (inferred
from the ruleset's empty bypass list) which classic protection does not actually
have.

## Corrections to #77

Three of #77's seven acceptances no longer stand:

- **SAST** resolved on its own, 8 → 10.
- **Vulnerabilities** — #77 kept `pytest==8.4.2` to preserve Python 3.9. The floor
  moved to 3.11 and `pytest==9.1.1` was taken; that advisory is gone.
- **Branch-Protection** — #77 declined a classic admin PAT as the reason for the
  score. Scorecard reads rulesets without one, so that reasoning was never valid.

The replacement `brace-expansion` advisories were briefly accepted here on the
grounds that upstream hadn't patched and Dependabot would raise it. Both false:
5.0.8 shipped 2026-07-23 and 5.0.9 on 2026-07-30, and Dependabot auto-dismisses
dev-scope alerts. Nineteen days unapplied. *"Wait for upstream"* needs someone to
check upstream; *"the bot will tell us"* needs the bot to be watching.

## Decision

Accept the above. Do not delete the npm-upgrade step, take on OSS-Fuzz, add an
admin PAT to CI, or weaken the ruleset to score better.

Update this file **in place** when a score moves, and prefer deleting a
justification to extending it.
