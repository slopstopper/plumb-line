# Tracking dialect — plumb-line

Recorded by `recursive-spine-bootstrap`, run against this repo on 2026-08-11
(issue [#215](https://github.com/slopstopper/plumb-line/issues/215)).

This repo was **partially** conforming before the stamp: it originated the
deferral-label discipline the convention later generalised, and its branch
names already carried issue numbers. The stamp is therefore mostly a
*record of what exists*, not an installation of new machinery — the
sequencing agreed on #215.

## Modules

- **Deferral (mandatory):** label **`audit-deferral`** — an alias, not the
  convention's default `deferred`. The name predates the convention and is
  cited from `CLAUDE.md`, `docs/dogfood.md`, and `ROADMAP.md`; renaming it
  would break those references and rewrite ~20 existing issues for no
  epistemic gain.

  **Scope broadened at the stamp.** The label previously read "Deferred
  finding from a plumb-line self-audit (dogfooding)" — audit findings only,
  narrower than principle 3, which requires *every* postponement to carry a
  record. It now reads "Postponed with a record — principle 3" and covers
  deferrals from any source: audit, dogfood, review, or handover. No
  existing issue was relabelled; the broadening is additive.
- **Gap:** label `gap`. Referents already exist —
  `docs/ossf-silver-gap-analysis.md` and the periodic self-audits.
- **Debt:** label `inherited-debt`, for known-incomplete edges handed over
  from a closed unit (principle 4).
- **Lane:** **declined at the stamp.** No tokenomics playbook exists in this
  repo, so there were no tier names on the record to use, and the convention
  ships no defaults. Revisit if this repo's work is ever routed across model
  tiers.

## Dialect

Unit of work = **issue**. No local alias; the convention's vocabulary
(issue, milestone, deferral) is used as-is.

**Branches:** `<prefix>/<issue>-<slug>`, where `<prefix>` is a
conventional-commit type (`feat`, `fix`, `docs`, `chore`, `ci`, `test`) —
e.g. `feat/139-report-format-validator`, `docs/77-scorecard-residuals`.
This was already the practice before the stamp. Release branches
(`release/v0.8.0`) are the deliberate exception: they carry a version, not
an issue.

**PRs** say `Closes #N` and list the debts they leave behind. The PR
template also restates the four requirements CI already enforces (single
change, failing-test-first, DCO sign-off, `CHANGELOG.md` under
`[Unreleased]`) — a reminder pointing at `CONTRIBUTING.md`, not a new rule.

### Local label conventions this repo adds

- **`track:*`** (`track:portable`, `track:boundaries`, `track:agent-state`,
  `track:ecosystem`, `track:skills`, `track:runtime`) — parallel tracks,
  deliberately unscheduled. Established by
  [#203](https://github.com/slopstopper/plumb-line/pull/203).

  **The rule:** every open issue carries *exactly one* of a release
  milestone (= scheduled) or a `track:*` label (= deliberately
  unscheduled). An issue with neither is a tracking bug, not a backlog
  item. Full rationale in
  [`ROADMAP.md` § How this backlog is organised](../ROADMAP.md).

  These were previously modelled as *milestones*, which made them
  permanently "stalled" by construction and trained the eye to ignore the
  stalled signal — the reason the milestone namespace is now releases only.
- **`feedback`** — referenced by `.github/ISSUE_TEMPLATE/feedback.yml` but
  **not created**; GitHub silently drops unknown labels, so feedback issues
  have been filed unlabelled. Filed as
  [#231](https://github.com/slopstopper/plumb-line/issues/231) at the stamp
  rather than fixed in passing, since the label's colour and description
  are the owner's call.

### Milestones

Milestone namespace is **releases only** (`v0.9.0 — Honest over time`,
`v0.10.0 — Refuse and explain`). A milestone means "these ship together, at
a version", so a stalled release milestone is always a real signal.

### The deferral outbox (local rule, stronger than principle 3)

Principle 3 requires that deferral be *recorded*. This repo additionally
requires that it *terminate*: at each release-scoping moment, every open
`audit-deferral` older than **30 days** is either scheduled into the next
release or closed with a written waiver. No third option, no silent aging.
Same shape as the provenance ratchet (#26) — don't demand zero, refuse
regression. Stated in [`ROADMAP.md`](../ROADMAP.md).

### Depth (sub-issues)

None in use as of the stamp — verified, not assumed. Depth is
moment-triggered: a tree is evidence that a moment happened, not a planning
aesthetic. Flat issues remain the norm here.

## Spine board

**Board owner:** `slopstopper` (the org).

**`SPINE_BOARD_NUMBER`: 3** — "Spine — public",
<https://github.com/orgs/slopstopper/projects/3> (public).

Board **#2** ("Spine", private) is **closed** and is not the board to use.
Note that `recursive-spine`'s own dialect note at plugin version 0.10.0
still records `SPINE_BOARD_NUMBER: 2`; that is stale relative to this
finding.

**Membership, as added (2026-08-11):** 41/41 open issues on the board — 15
were already present from an earlier snapshot, 26 were backfilled at the
stamp, 26/26 `item-add` calls succeeded.

Verified through each issue's `projectItems` in GraphQL, **not** through
`gh project item-list`: the project-side read path lagged behind the
writes, reporting 29 items where the issue-side query saw all 41. Membership
claims about this board should use the issue-side query.

**Auto-add: not enabled — pending owner action.** Projects v2 auto-add
workflows are UI-only and cannot be created via the `gh` CLI or the public
GraphQL API. **Consequence, stated plainly:** until auto-add is switched on,
the board does not pick up newly-filed issues, and the membership above is a
point-in-time snapshot that will silently go stale — which is exactly how it
had already drifted to 15/41 before this stamp. Tracked as
[#230](https://github.com/slopstopper/plumb-line/issues/230) — a filed issue,
not a memory. Settings:
<https://github.com/orgs/slopstopper/projects/3/settings/workflows>

## Kin offers, as answered

- **plumb-line wiring** (epistemic enforcement offer): **not applicable** —
  this repo *is* plumb-line. Its principles already govern its own code
  (`CONTRIBUTING.md` § "Principles come first"), and the audit skill is run
  against it as dogfooding.
- **tokenomics wiring** (lane-semantics pointer offer): **declined**, as a
  consequence of declining the lane module — there are no `lane:*` labels
  here to give semantics to. Revisit together with the lane module.

## pollinate: hives

**Not recorded at the stamp** — outside the bootstrap's interview, and the
open question that motivated half of #215. Until a `pollinate:` section
exists here, `recursive-spine-pollinate` will fall back to its documented
default hive (`slopstopper/recursive-spine`, public), which is an
assumption rather than a recorded answer. The public/private hive split is
precisely the thing that should not be assumed, so the gap is named here
rather than papered over.

Run `recursive-spine-pollinate` (it interviews for hives) or
`recursive-spine-scaffold` to record it.

## Not stamped, and why

- **Lane module** — declined; no tier names on the record. See Modules.
- **`scripts/spine-audit.sh` / `scripts/spine-doctor.sh`** — the digest's
  convention and installation health checks. Not part of the bootstrap;
  their absence is why `recursive-spine-digest` skipped those checks in the
  session that opened #215. The deferral and milestone halves of the digest
  work without them.
- **Scaffold parts** — this repo already has several under its own names
  (ADRs in `docs/adr/`, a rules codex in `reference/portable-principles.md`,
  CI gates in `.github/workflows/`, session memory). Recording them as
  scaffold parts is `recursive-spine-scaffold`'s job, not the bootstrap's.
