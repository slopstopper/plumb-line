# OpenSSF Scorecard — accepted residuals

**Scorecard run:** 2026-08-11 · **Overall: 7.0/10** · re-checked live for this
record, not transcribed from a previous one.

This file records why each non-perfect Scorecard check is **accepted**,
**deferred**, or **resolved** — rather than left unexplained. It exists because a
score with no recorded reasoning is indistinguishable from a score nobody looked
at ([#77](https://github.com/slopstopper/plumb-line/issues/77)).

**None of the residuals is an exploitable vulnerability in shipped code.**
Scorecard's per-check "score" reflects how important the check is judged to be,
not the severity of anything found.

Re-check with:

```bash
curl -s https://api.scorecard.dev/projects/github.com/slopstopper/plumb-line
```

## Current state

| Check | Score | Status |
| --- | --- | --- |
| Binary-Artifacts, CI-Tests, Dangerous-Workflow, Dependency-Update-Tool, License, Packaging, SAST, Security-Policy, Token-Permissions | 10 | — |
| Pinned-Dependencies | 9 | accepted |
| Vulnerabilities | 8 → **resolved** | patched, see below |
| Contributors | 6 | accepted (structural) |
| Branch-Protection | 5 | accepted (Scorecard is correct) |
| Maintained | 0 | self-resolving |
| Code-Review | 0 | structural |
| Fuzzing | 0 | out of scope |
| CII-Best-Practices | 0 | **actionable — see below** |
| Signed-Releases | −1 | not applicable |

## Resolved since #77 was filed

Recorded because a stale acceptance is worse than none — it justifies a
constraint that no longer exists.

- **SAST: 8 → 10.** CodeQL covered 18/30 commits when #77 was written; it now
  covers the window Scorecard samples. Resolved by the passage of commits, as
  predicted.
- **Vulnerabilities: the original rationale is obsolete.** #77 accepted
  `GHSA-6w46-j5rx-g56g` (`pytest==8.4.2`) on the grounds that pytest ≥9 requires
  Python ≥3.10 and "fixing = dropping Python 3.9". The floor moved to **3.11**
  under the [support policy](../SUPPORT.md) and `pytest==9.1.1` was taken. That
  advisory is gone.
- **Vulnerabilities: the replacement pair was patchable, not acceptable.** The
  8/10 at the time of writing was two `brace-expansion` DoS advisories
  ([`GHSA-mh99-v99m-4gvg`](https://osv.dev/GHSA-mh99-v99m-4gvg),
  [`GHSA-rgw5-rvv9-x895`](https://osv.dev/GHSA-rgw5-rvv9-x895)). The first draft
  of this record **accepted** them, on the reasoning that they are transitive
  dev-only and that "Dependabot will raise it, no manual action".

  Both halves were wrong. Fixes shipped upstream in `5.0.8` (2026-07-24) and
  `5.0.9` (2026-08-03); the lockfiles pinned `5.0.7` while every consumer already
  required `^5.0.5`, so the patch needed one `npm update`. And Dependabot had
  **auto-dismissed** all four alerts as `scope: development`, so it was never
  going to raise anything.

  Resolved by updating both lockfiles to `5.0.9`. The lesson is recorded rather
  than quietly fixed: *"wait for upstream"* is only an acceptance if someone has
  checked that upstream has not already shipped, and *"the bot will tell us"* is
  only a backstop if the bot is actually watching that scope.

## Accepted residuals

### Pinned-Dependencies — 9/10

`release.yml` runs `npm install -g npm@11.18.0` (npm ≥11.5.1 is required for
trusted publishing). A global `-g` install cannot be hash-pinned. The version is
pinned exactly — the `@latest` float that originally triggered this is gone.

**Why accepted:** the only remaining "fix" is deleting the step, which would
break trusted publishing — trading a real supply-chain control for a
scoring one.

### Contributors — 6/10

Full marks need contributions from **≥3** organisations. Scorecard detects two
(`slopstopper`, `anthropics`) and normalises: 2 × 10/3 → 6.

**Why accepted:** this measures project reach, not security posture. It moves
when a third organisation contributes, which is not something to engineer.

### Branch-Protection — 5/10

`main` is governed by an **active repository ruleset**, `protect-main`
(id 18269324, no bypass actors). Force-pushes and deletion are disabled and
**code-owner review is required**. Its pull-request parameters are:

```
required_approving_review_count   0
dismiss_stale_reviews_on_push     false
require_last_push_approval        false
require_code_owner_review         true
```

Scorecard's `Warn` lines are therefore **accurate**, not a misread. An earlier
draft of this record claimed Scorecard was misreading the classic protection API
and that a classic admin PAT would be needed to see the truth. That was wrong on
both counts: Scorecard reads *rulesets*, which need no admin PAT, and stale-review
dismissal genuinely is off. The classic `/branches/main/protection` endpoint
returns `dismiss_stale_reviews: true`, but the ruleset is what governs merges —
citing only the endpoint that agreed with us was the error.

**What is actually true:** `enforce_admins` is `false`, and the ruleset requires
**zero** approvals, so the review requirement is not binding on the maintainer who
merges. Scorecard measured **0 of 9 changesets approved** — that is the honest
picture, and issue #77 stated it plainly ("solo maintainer admin-merges own PRs")
before this record briefly lost it.

**Why accepted:** a single-maintainer project cannot require an approval it has
nobody to obtain. Requiring one would stop all merging; requiring two (what
Scorecard wants for full marks) is further still. Code-owner review is enabled
because it costs nothing today and becomes meaningful the moment a second person
exists.

**Revisit when:** a second maintainer joins — then raise
`required_approving_review_count` to 1, enable `dismiss_stale_reviews_on_push`
and `require_last_push_approval`, and set `enforce_admins`. All four are cheap
with two people and self-defeating with one.

### Maintained — 0/10

*"Repository created within the last 90 days."* Created **2026-06-28**; clears
automatically around **2026-09-26**. Pure repository age.

### Code-Review — 0/10

Scorecard counts **approved** changesets and found 0 of 9.

The mechanism is worth stating precisely, because it is easy to describe wrongly:
GitHub does not permit approving your own pull request. The zero comes from PRs
being merged with **no approval at all** — the ruleset requires zero, and
`enforce_admins` is `false`, so an admin merge is unobstructed.

**Why accepted:** structural to a single-maintainer project, and the same
condition as Branch-Protection above. It moves when someone else reviews, not
through configuration.

### Fuzzing — 0/10

No OSS-Fuzz integration.

**Why accepted:** out of proportion for a small provenance library. The JS side
already runs property-based tests (`fast-check`), which Scorecard's fuzzing check
does not recognise. Integrating OSS-Fuzz is a substantial ongoing commitment for
a library whose inputs are small structured envelopes.

### Signed-Releases — −1 (inconclusive)

*"No releases found."* The project **does** publish GitHub Releases — 13 of them,
v0.1.0 through v0.7.3, created by `release.yml`. Scorecard counts only releases
carrying **assets**, and these carry none, so it reports nothing found rather
than nothing signed. Stated precisely because the check's own wording sends a
reader looking for missing releases that are in fact there.

**Why accepted:** npm and PyPI trusted publishing already provides provenance
attestation at the registries — the place consumers actually install from.
Duplicating signed tarballs onto GitHub Releases would add a second artifact
path to keep honest, for a check scored `−1` (not counted) either way.

## Actionable, not accepted

### CII-Best-Practices — 0/10 — **cause identified**

Scorecard reports *"no effort to earn an OpenSSF best practices badge
detected"*. The project in fact holds **silver** — entry
[13453](https://www.bestpractices.dev/projects/13453), passing 2026-07-01,
silver 2026-07-02.

The entry still records the **pre-rename repository URL**:

```
badge_level  silver
repo_url     https://github.com/effythealien/plumb-line
```

Scorecard resolves a Best Practices entry by the repository URL it is scanning
(`github.com/slopstopper/plumb-line`), finds no entry registered against it, and
scores 0. The badge work is complete; the *registration* was left behind by the
organisation rename.

**Not accepted — actionable.** The fix is to update `repo_url` (and
`homepage_url`) on entry 13453 to the current URL, which requires the badge
account and so cannot be done from the repository. Tracked as
[#217](https://github.com/slopstopper/plumb-line/issues/217).

Worth naming the class: an organisation rename updates everything *inside* the
repository, and silently strands every **external registration that points back
at it**. This one was visible only because a scoring check disagreed with a
badge in the README — a discrepancy nobody had reconciled.

## Decision

Accept the residuals above. Do **not** delete the npm-upgrade step or take on
OSS-Fuzz to move the number, and do not weaken the ruleset to score better. Let
*Maintained*, *Code-Review* and *Contributors* trend on their own — all three are
functions of time and other people, not configuration.

**CII-Best-Practices is not accepted**: the cause is identified (a stale
`repo_url` on badge entry 13453) and the fix is a two-field edit on
bestpractices.dev, tracked as
[#217](https://github.com/slopstopper/plumb-line/issues/217).

Re-run this analysis at each release whose diff touches CI, release tooling, or
dependency pinning — and update it in place rather than appending, since a
residual record that accumulates stale entries stops being readable. The
"Resolved since" section above is what that update looks like.
