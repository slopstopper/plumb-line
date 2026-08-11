# OpenSSF Scorecard — accepted residuals

**Scorecard run:** 2026-08-11 · **Overall: 7.0/10** · re-checked live for this
record, not transcribed from a previous one.

This file records why each non-perfect Scorecard check is **accepted**,
**deferred**, or **resolved** — rather than left unexplained. It exists because a
score with no recorded reasoning is indistinguishable from a score nobody looked
at ([#77](https://github.com/slopstopper/plumb-line/issues/77)).

**None of the residuals is an exploitable vulnerability in shipped code.**

A note on reading the numbers, since it is easy to get backwards: a check's
**score** *is* its finding (Vulnerabilities scored 8 because two advisories were
found — 10 minus 2). What encodes importance is the separate per-check **risk
level**, which weights the aggregate. So a low score means "this check found
something", not "this check matters more than others".

Re-check with:

```bash
curl -s https://api.scorecard.dev/projects/github.com/slopstopper/plumb-line
```

## Current state

| Check | Score | Status |
| --- | --- | --- |
| Binary-Artifacts, CI-Tests, Dangerous-Workflow, Dependency-Update-Tool, License, Packaging, SAST, Security-Policy, Token-Permissions | 10 | — |
| Pinned-Dependencies | 9 | accepted |
| Vulnerabilities | 8 | **patched here, awaiting re-scan** |
| Contributors | 6 | accepted (structural) |
| Branch-Protection | 5 | accepted (Scorecard is correct) |
| Maintained | 0 | self-resolving |
| Code-Review | 0 | structural |
| Fuzzing | 0 | out of scope |
| CII-Best-Practices | 0 | **fix applied, awaiting re-scan** |
| Signed-Releases | −1 | not applicable |

## Changed since #77 was filed

Two of #77's seven acceptances no longer stand. One resolved on its own; one was
never a valid acceptance. Recorded rather than deleted, because a stale
acceptance is worse than none — it justifies a constraint that no longer exists,
and the failure mode is invisible unless someone writes down what expired.

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

  Both halves were wrong. Upstream published `5.0.8` on **2026-07-23** and
  `5.0.9` on **2026-07-30** (npm publish times, not the later advisory
  publication dates); the lockfiles pinned `5.0.7` while every consumer already
  required `^5.0.5`, so the patch needed one `npm update`. The fix was therefore
  available and unapplied for **twelve days**. And Dependabot had
  **auto-dismissed** all four alerts as `scope: development`, so it was never
  going to raise anything.

  Both lockfiles are updated to `5.0.9` in the change that introduced this
  record. **Scorecard has not re-scanned**, so the check still reads 8 in the
  table above — patched is not the same claim as observed-resolved, and this
  record does not get to make the second one early (see the same discipline
  applied to CII-Best-Practices below).

  The reasoning is recorded rather than quietly deleted: *"wait for upstream"* is
  only an acceptance if someone has checked that upstream has not already
  shipped, and *"the bot will tell us"* is only a backstop if the bot is actually
  watching that scope.

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

**Both systems are live at once**, and this took two wrong drafts to state
correctly. Classic branch protection is *also* configured on `main`,
independently of the ruleset:

```
required_approving_review_count   1
dismiss_stale_reviews             true
enforce_admins                    false
required status checks            JavaScript (Node 20), Manifest versions agree,
                                  Python 3.11, Python 3.13
```

That fourth required check appears in no ruleset, which proves the classic
config is not a derived view of one. GitHub applies both, most-restrictive-wins:
**for any non-admin contributor, one approval is required and stale reviews are
dismissed.**

Two earlier drafts of this section were wrong in opposite directions. The first
claimed Scorecard was misreading and that an admin PAT was needed — false; it
reads rulesets without one. The second claimed "the ruleset is what governs
merges" and that stale-review dismissal is genuinely off — also false, because
classic protection is live too. Scorecard in fact merges both sources: its detail
line `required approving review count is 1` can only come from the classic API,
since the ruleset says 0.

**What is actually true:** `enforce_admins` is `false`, so none of it binds the
maintainer who merges. Scorecard measured **0 of 9 changesets approved** — that
is the honest picture. Issue #77 said as much in one clause when the project had
a single maintainer ("solo maintainer admin-merges own PRs"); this record twice
replaced that plain account with a more architectural and less true one. The
maintainer count has since changed (see below); the merge behaviour has not.

**Why accepted:** the `slopstopper` org has two members, but they work on separate
projects. The second member contributes to plumb-line by **testing it against
real repositories and giving feedback directly**, not by reviewing pull requests.
So there is a second person, and there is still nobody in the PR-approval loop —
requiring an approval would block merging without adding a reviewer.

That distinction matters for the revisit trigger below: the constraint is not
"only one person exists" (untrue), it is "review is not how this project
collaborates" (true, and a choice rather than a limitation). Code-owner review is
enabled because it costs nothing and becomes binding the moment that changes.

**Revisit when:** PR review becomes part of how this project is worked on —
*not* "when a second maintainer joins", which has already happened and changed
nothing here. Note which system each setting lives in, because they are not
interchangeable:

- **Ruleset `protect-main`:** raise `required_approving_review_count` to 1 (2 for
  full marks), enable `dismiss_stale_reviews_on_push` and
  `require_last_push_approval`.
- **Classic protection:** enable `enforce_admins`. There is no ruleset equivalent
  — rulesets express the same idea as an empty `bypass_actors` list, which is
  already the case, so the admin bypass here comes from the classic config.

All are cheap with two people and self-defeating with one.

### Maintained — 0/10

*"Repository created within the last 90 days."* Created **2026-06-28**; clears
automatically around **2026-09-26**. Pure repository age.

### Code-Review — 0/10

Scorecard counts **approved** changesets and found 0 of 9.

The mechanism is worth stating precisely, because it is easy to describe wrongly:
GitHub does not permit approving your own pull request. The zero comes from PRs
being merged with **no approval at all** — the ruleset requires zero, and
`enforce_admins` is `false`, so an admin merge is unobstructed.

**Why accepted:** same condition as Branch-Protection above — the project has a
second org member, but they contribute through direct testing and feedback rather
than PR approval, so no changeset acquires one.

Worth being honest about what this check does and does not see. Every PR in this
cycle *was* independently reviewed, by a separate agent, and that review found
real defects in three of four previously-unreviewed PRs — including in this very
document, three rounds running. None of that is visible to Scorecard, which
counts GitHub approvals. Equally, an agent review is not a human approval and
should not be presented as satisfying the check: the score is 0 and the record
says so. The point is that "0/10 Code-Review" measures a specific artifact, not
whether the code was looked at.

It moves when someone else approves changesets, not through configuration.

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

### CII-Best-Practices — 0/10 — **cause found and fixed, awaiting re-scan**

Scorecard reports *"no effort to earn an OpenSSF best practices badge
detected"*. The project in fact holds **silver** — entry
[13453](https://www.bestpractices.dev/projects/13453), passing 2026-07-01,
silver 2026-07-02.

**Cause (since fixed):** the entry recorded the **pre-rename repository URL** —
`repo_url` and `homepage_url` both read
`https://github.com/effythealien/plumb-line`. Scorecard resolves a Best Practices
entry by the repository URL it is scanning (`github.com/slopstopper/plumb-line`),
found no entry registered against it, and scored 0. The badge work was complete;
the *registration* had been left behind by the organisation rename.

**Not accepted — fix applied 2026-08-11.** Entry 13453 now records
`repo_url` and `homepage_url` as `https://github.com/slopstopper/plumb-line`.
The change is on the badge account, not in this repository, so nothing here
proves it: the score is expected to move on the next scheduled `scorecard.yml`
run, and [#217](https://github.com/slopstopper/plumb-line/issues/217) stays open
until it is observed rather than closed on the strength of having acted.

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
