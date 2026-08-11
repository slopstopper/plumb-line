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
| Vulnerabilities | 8 | accepted |
| Contributors | 6 | accepted (structural) |
| Branch-Protection | 5 | accepted (partly a misread) |
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
  advisory is gone; the current 8/10 is a *different* pair (below).

## Accepted residuals

### Vulnerabilities — 8/10

Two advisories, both in **`brace-expansion`**:

- [`GHSA-mh99-v99m-4gvg`](https://osv.dev/GHSA-mh99-v99m-4gvg) — DoS via
  unbounded expansion length
- [`GHSA-rgw5-rvv9-x895`](https://osv.dev/GHSA-rgw5-rvv9-x895) — DoS via
  unbounded intermediate arrays

Both are availability-only (`C:N/I:N/A:H`) and reachable only by expanding
attacker-controlled brace patterns.

**Why accepted:** `brace-expansion` is a *transitive dev* dependency of the
lint/test toolchain, present in `primitives/js/package-lock.json` and
`adapters/js/package-lock.json` only. **Both published packages declare zero
runtime dependencies** — nothing here ships to a consumer. The exposure is a
developer running our own test suite against a hostile glob, which is not a
threat this project defends against ([threat model](threat-model.md)).

**Revisit when:** the upstream toolchain releases a patched transitive; Dependabot
will raise it. No manual action.

### Pinned-Dependencies — 9/10

`release.yml` runs `npm install -g npm@11.18.0` (npm ≥11.5.1 is required for
trusted publishing). A global `-g` install cannot be hash-pinned. The version is
pinned exactly — the `@latest` float that originally triggered this is gone.

**Why accepted:** the only remaining "fix" is deleting the step, which would
break trusted publishing — trading a real supply-chain control for a
scoring one.

### Contributors — 6/10

Scorecard wants contributions from ≥2 organisations; it detects `slopstopper` and
`anthropics`.

**Why accepted:** this measures project popularity, not security posture. It
moves when other organisations contribute, which is not something to engineer.

### Branch-Protection — 5/10

Protection is real and verified live via the API: 1 approving review required,
**code-owner review required**, force-pushes disabled, deletion disabled.

Scorecard's own detail lines partly contradict the API. It reports *"'stale
review dismissal' is disabled on branch 'main'"* while
`/branches/main/protection` returns `dismiss_stale_reviews: true`. Scorecard is
running with the default `GITHUB_TOKEN`, which cannot read every protection
field; the accurate reading requires a classic **admin PAT** stored as
`repo_token`.

**Why accepted:** a long-lived admin PAT in CI is a materially worse
supply-chain risk than an under-reported score. The remaining points also want
`enforce_admins=true`, which locks a solo maintainer out of their own repository.

**Revisit when:** a second maintainer joins — at which point `enforce_admins`
stops being self-defeating and the PAT tradeoff can be re-argued.

### Maintained — 0/10

*"Repository created within the last 90 days."* Created **2026-06-28**; clears
automatically around **2026-09-26**. Pure repository age.

### Code-Review — 0/10

Scorecard counts approved changesets. A solo maintainer approving their own PRs
scores zero by construction, even though branch protection requires a review and
CODEOWNERS is in place.

**Why accepted:** structural to a single-maintainer project. It improves only as
PRs receive approvals from someone else.

### Fuzzing — 0/10

No OSS-Fuzz integration.

**Why accepted:** out of proportion for a small provenance library. The JS side
already runs property-based tests (`fast-check`), which Scorecard's fuzzing check
does not recognise. Integrating OSS-Fuzz is a substantial ongoing commitment for
a library whose inputs are small structured envelopes.

### Signed-Releases — −1 (inconclusive)

*"No releases found."* The project tags releases (`v0.7.3`) and publishes to npm
and PyPI via trusted publishing, but does not attach signed artifacts to GitHub
Releases, which is what this check inspects.

**Why accepted:** npm and PyPI trusted publishing already provides provenance
attestation at the registries — the place consumers actually install from.
Duplicating signed tarballs onto GitHub Releases would add a second artifact
path to keep honest, for a check scored `−1` (not counted) either way.

## Actionable, not accepted

### CII-Best-Practices — 0/10

Scorecard reports *"no effort to earn an OpenSSF best practices badge
detected"* — but the project **has** a Best Practices entry
([13453](https://www.bestpractices.dev/projects/13453)), linked from the README.

This is the one residual that is neither a deliberate tradeoff nor
self-resolving: either the badge entry is below the `passing` threshold, or
Scorecard cannot associate it with this repository. Both are fixable and neither
has been investigated.

**Not accepted.** Tracked separately rather than absorbed into this record,
because filing it under "accepted residuals" would be exactly the laundering
this document exists to prevent.

## Decision

Accept the residuals above. Do **not** delete the npm-upgrade step, add an admin
PAT to CI, or take on OSS-Fuzz to move the number. Let *Maintained* and
*Code-Review* trend on their own. Investigate **CII-Best-Practices** as ordinary
work.

Re-run this analysis at each release whose diff touches CI, release tooling, or
dependency pinning — and update it in place rather than appending, since a
residual record that accumulates stale entries stops being readable. The
"Resolved since" section above is what that update looks like.
