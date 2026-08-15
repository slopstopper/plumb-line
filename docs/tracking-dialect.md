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
- **`feedback`** — `006B75`, "Use-case report from someone running
  plumb-line on their own code". Referenced by
  `.github/ISSUE_TEMPLATE/feedback.yml` but **not created** until
  2026-08-12; GitHub silently drops labels a form references but that do
  not exist. Found at the stamp
  ([#231](https://github.com/slopstopper/plumb-line/issues/231), fixed).

  **Honest denominator:** the defect was **latent, not realised** — zero
  issues have ever been filed through the form, so nothing actually lost a
  label and no backfill was needed. What the bug threatened was the query:
  `--label feedback` returns empty both when no feedback exists and when
  feedback exists but was mislabelled, and those are very different states.

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

### Historical URLs are not updated

The repo moved from `effythealien/plumb-line` to `slopstopper/plumb-line`.
The rename was applied to **live** documents only. Records keep the URLs
they were written with, because a record states what was true when it was
written:

| File | Old-org links | Why they stay |
| --- | --- | --- |
| `CHANGELOG.md` | 37 | released sections describe past releases (the `[Unreleased]` section carries none) |
| `docs/dogfood.md` | 13 | versioned sections record dated dogfood passes |
| `docs/validation-results.md` | 3 | dated validation runs |
| `docs/adr/0009-…` | 2 | ADRs are append-only |

**Do not "fix" these.** GitHub redirects the old paths, so they resolve;
rewriting them would make a record claim a URL that did not exist when the
record was made.

Live documents — README, ROADMAP, CONTRIBUTING, the specs, this note — use
`slopstopper/plumb-line`. `ROADMAP.md` was corrected on 2026-08-12: seven
links in § Planned pointed at the old org while describing *open* work in
the future tense, which is a live claim wearing a stale URL, not a record.

The test: **is this sentence describing what is true now, or what was true
then?** Now → current org. Then → leave it.

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

**This board is plumb-line-only, and that is now a deliberate choice.** A
cross-project board was investigated on 2026-08-12 and found unbuildable
with auto-add, on two independent limits confirmed in the UI:

1. **Auto-add cannot cross an owner boundary.** A user-owned project's
   auto-add repository picker does not list organisation repositories at
   all — so a personal aggregate board cannot pull in `slopstopper/*`,
   even though issues from those repos can be added to it manually via
   `gh project item-add` (a different code path, and one that works).
2. **The workflow count is capped per project by plan.** `slopstopper` is
   on GitHub Free: **one** auto-add workflow per project. Each workflow
   targets one repository, so one board can automatically track exactly
   one repo.

Together these mean **a self-maintaining cross-project board is not
achievable on this plan** — not merely unconfigured. One board per repo is
the only shape auto-add supports, and cross-project aggregation needs
either manual `item-add` calls or a scheduled job. Recorded here so the
constraint is not rediscovered; filed upstream as
[recursive-spine#128](https://github.com/slopstopper/recursive-spine/issues/128),
since the "Spine board" is a spine concept and not specific to this repo.

plumb-line is unaffected in practice: this board is already single-repo,
so its one available auto-add slot is sufficient, and
[#230](https://github.com/slopstopper/plumb-line/issues/230) remains
achievable as written.

## Kin offers, as answered

- **plumb-line wiring** (epistemic enforcement offer): **not applicable** —
  this repo *is* plumb-line. Its principles already govern its own code
  (`CONTRIBUTING.md` § "Principles come first"), and the audit skill is run
  against it as dogfooding.
- **tokenomics wiring** (lane-semantics pointer offer): **declined**, as a
  consequence of declining the lane module — there are no `lane:*` labels
  here to give semantics to. Revisit together with the lane module.

## pollinate: hives

Recorded 2026-08-12 at the scaffold run. This was the open question behind
half of #215: the bootstrap left it unanswered rather than assuming, and
`recursive-spine-pollinate` was falling back to its default hive — which
happened to be right, but as an assumption rather than an answer.

- **Public hive:** `slopstopper/recursive-spine` (`pollen/`) — pollen whose
  proof is public. plumb-line is a public repo, so its proofs route here by
  default. Records must stay self-contained: no reference a reader cannot
  resolve.
- **Private hive:** `effythealien/private-hive` — pollen whose proof is
  personal or private-scope. Nothing from this repo routes there unless a
  specific proof is private.

Routing rule: **pollen inherits the visibility scope of its proof**, not the
visibility of the repo it is captured from. Declassification into the public
hive is a deliberate, scrubbed act.

### Pollen sourced from this repo

Four records in the public hive name plumb-line as their source. All are
schema-conformant and paired with `pollen`-labelled issues:

| Record | Source | Stage |
| --- | --- | --- |
| `deferral-outbox` | [#203](https://github.com/slopstopper/plumb-line/pull/203) | seedling |
| `milestones-are-releases-only` | [#203](https://github.com/slopstopper/plumb-line/pull/203) | seedling |
| `decisions-block` | [#213](https://github.com/slopstopper/plumb-line/pull/213) | seedling → **adopted here 2026-08-12** |
| `independent-review-layer` | [#213](https://github.com/slopstopper/plumb-line/pull/213) | seedling → **adopted here 2026-08-12** |

**The gap the scaffold run found.** `decisions-block` and
`independent-review-layer` were proved in this repo, exported to the hive,
and never adopted *here* — `decisions-block`'s own transplant instructions
say to put it in the repo's agent-instructions file "so it survives across
sessions rather than living in one conversation's memory", and in the
source repo it lived only in the pollen record. Both are now in
`AGENTS.md`.

Note this is **not** a `transplants:` entry: a transplant is another
project taking a pattern up, and a source repo adopting its own proof is
not that. It is a source-side adoption gap, recorded here.

The first two remain unadopted-as-text because they are already *in force*
here structurally — the outbox rule and the releases-only milestone
namespace are live in `ROADMAP.md` and this note. They were extracted from
practice, not imported into it.

## scaffold (this installation)

Recorded per the scaffold skill's interview, run 2026-08-12 immediately
after the tracking stamp. Four of the six parts were **already present**
under this repo's own names — the stamp records them rather than adding
machinery.

- **Rules codex:** accepted — `AGENTS.md` extended. It deliberately
  **points rather than copies**: every durable fact already lives in a
  committed doc, so restating values would create the second source of
  truth this repo exists to prevent. What it adds is the map (which file
  holds what), four load-bearing warnings an agent gets wrong by default,
  the moments map, and the two adopted pollen patterns.

  Requested at the interview: `AGENTS.md` must be usable if the owner's
  local `CLAUDE.md` is ever lost. Satisfied by the map, not by
  duplication — a map goes stale far more slowly than a copy, since paths
  change rarely and version numbers change constantly. Audited before
  writing: every durable CLAUDE.md fact was already covered in
  `CONTRIBUTING.md`, `DEVELOPMENT.md`, `RELEASING.md`, `docs/api.md`,
  `primitives/PARITY.md`, or `docs/threat-model.md`.
- **ADR directory:** **already present** — `docs/adr/` with 13 real ADRs
  and a README, append-only. Nothing stamped, nothing backfilled; an
  invented example ADR is banned and no real decision was un-recorded.
- **CI gates:** **already present** — `.github/workflows/ci.yml` carries a
  named gate set (manifest agreement, bundle sync, wire-version prose,
  conformance, lint, per-language suites). This repo is the source proof
  of the `truth-gate-ci` pollen. Extended by one step, not replaced.
- **Session memory:** **declined** — repo-level session memory is not in
  use here; the owner's memory convention lives at the environment level.
  Same answer recursive-spine recorded for itself.
- **Constraints file + drift gate:** accepted — `docs/constraints.md`
  plus `scripts/check-constraints-drift.sh`, wired as one named step in
  the existing `versions` job (checkout moved to `fetch-depth: 0`; pinned
  sha reads fail on a shallow clone). `scripts/check_version_prose.py` is
  the hand-rolled ancestor of the same idea applied to one constraint and
  stays as-is; the two check different things.

  The file recorded a real disagreement rather than flattening it:
  `engines.node >= 16` published while CI tested Node 20 only, leaving
  16–19 supported-by-declaration and unverified-by-test. (Since
  resolved — the floor was raised to `>= 20` and the matrix exercises
  it, GH #233; kept here as the worked example it was.)
- **The loop:** **already present elsewhere** — declined *locally*.
  `slopstopper/recursive-spine`'s `spine-loop.yml` already sweeps this
  repo (`repos: "… slopstopper/plumb-line …"`). A local workflow would
  double the sweep and the nudges.

### Kin offers, as answered at the scaffold run

- **plumb-line guard wiring** for the stamped gates: **not applicable** —
  this repo is plumb-line (see "Kin offers, as answered" above).
- **tokenomics playbook pointer**: **declined**, unchanged from the
  bootstrap — still no playbook in this repo and still no `lane:*` labels
  to give semantics to.

## Not stamped, and why

- **Lane module** — declined; no tier names on the record. See Modules.
- **`scripts/spine-audit.sh` / `scripts/spine-doctor.sh`** — the digest's
  convention and installation health checks. Not part of the bootstrap;
  their absence is why `recursive-spine-digest` skipped those checks in the
  session that opened #215. The deferral and milestone halves of the digest
  work without them.
- **Scaffold parts** — no longer outstanding. Recorded in the `scaffold`
  section above at the 2026-08-12 run; four of six were already present
  under this repo's own names.
