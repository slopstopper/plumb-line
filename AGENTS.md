# AGENTS.md — plumb-line

Instructions for coding agents working in this repository, and the map a
new contributor needs to find everything else.

This file deliberately **points rather than copies**. Every durable fact
about this repo already lives in a committed document; restating values
here would create a second source of truth that drifts — the failure this
repo exists to prevent. What is written here is what you cannot get by
reading one file: *which* file, and *that* it matters.

## Where things are written down

| You need | It is in |
| --- | --- |
| How to build and test each component | [`DEVELOPMENT.md`](DEVELOPMENT.md) |
| How to contribute, and what a PR must satisfy | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| How releases are cut and published | [`RELEASING.md`](RELEASING.md) |
| The nine principles this project enforces — and is held to | [`reference/portable-principles.md`](reference/portable-principles.md) |
| The envelope schema (the formal spec) | [`primitives/SPEC.md`](primitives/SPEC.md) |
| The two API shapes, JS vs Python | [`docs/api.md`](docs/api.md) |
| Cross-language parity, and the case table that enforces it | [`primitives/PARITY.md`](primitives/PARITY.md), [`primitives/conformance/cases.json`](primitives/conformance/cases.json) |
| What is guaranteed, and what is only tamper-*evident* | [`docs/threat-model.md`](docs/threat-model.md), [`SECURITY.md`](SECURITY.md) |
| Exact-valued global constraints (versions, floors, contracts) | [`docs/constraints.md`](docs/constraints.md) |
| Why a past decision was made | [`docs/adr/`](docs/adr/) — append-only |
| What is planned, and how the backlog is organised | [`ROADMAP.md`](ROADMAP.md) |
| This repo's tracking vocabulary and modules | [`docs/tracking-dialect.md`](docs/tracking-dialect.md) |

## Four things that are load-bearing

Each is documented above. They are repeated here as *warnings* because
each is something an agent gets wrong by acting on a reasonable default.

1. **There is no root test command.** No root `package.json`. Each
   component is tested from its own directory. Running "the tests" from
   the repo root tests nothing. See [`DEVELOPMENT.md`](DEVELOPMENT.md).
2. **Parity is the central invariant.** JS and Python must behave
   *identically*. When you change combination or audit behaviour, change
   **both** implementations and add a row to `cases.json`. A divergence
   failing one suite is the system working. Never "fix" parity by editing
   prose — fix the code or the case table.
3. **This repo is held to its own principles.** The rules the audit skill
   applies to other people's code apply here. Don't launder uncertainty,
   hardcode a prior, or overstate maturity; use the maturity vocabulary
   (`current` / `planned`), not aspirational claims.
4. **New behaviour needs a failing test first.** Enforcement is proven by
   tests, not asserted.

## Tracking (recursive-spine convention)

Work state lives in GitHub issues and milestones, not in prose files.
- What's in flight: `gh issue list --assignee @me`
- Deferred work: `gh issue list --label audit-deferral`
- Branches: `<prefix>/<issue>-<slug>`; PRs say `Closes #N`.
- Deferral requires a filed issue. Handover files its debts before closing.
Dialect and modules for this repo: [docs/tracking-dialect.md](docs/tracking-dialect.md)

Two local rules go beyond the convention's baseline, both from
[`ROADMAP.md`](ROADMAP.md):

- **Every open issue carries exactly one** of a release milestone
  (= scheduled) or a `track:*` label (= deliberately unscheduled). Neither
  is a tracking bug, not a backlog item.
- **Deferrals have an outbox.** At each release-scoping moment, every open
  `audit-deferral` older than 30 days is either scheduled into the next
  release or closed with a written waiver. No third option.

## Moments map

When one of these happens, this is what handles it:

- postponing something → file an issue with `audit-deferral`; it must have a
  revisit condition, not a wish
- an audit or dogfood pass produces a finding → file it with `gap`; work
  issues cite the gaps they close
- closing a unit of work → `recursive-spine-handover` (files debts as
  `inherited-debt`, asks the pollen question, posts the closing record)
- something here just proved itself → `recursive-spine-pollinate` captures it
  to the hive (see the dialect note for hive routing)
- a durable decision gets made → add or amend an ADR in `docs/adr/`; a
  superseded decision is *marked*, never deleted
- scoping a release → drain the deferral outbox (see above) before the
  milestone is fixed
- a release diff touches `skills/`, `reference/portable-principles.md`,
  `primitives/`, or `adapters/` → run [`docs/release-harness.md`](docs/release-harness.md)
  before tagging
- "where does work stand?" → `recursive-spine-digest`

## Review: run an independent layer

Run a **separate** reviewer over each unit of work before it lands — a
subagent with its own context, not the one that wrote the code. Not
because the author was careless: tests written by the author encode the
author's assumptions, and the defects that survive are precisely the ones
those assumptions hide.

The author's own harnesses are good at **behaviour** — differential runs,
fuzzing, mutation. What they structurally cannot see are **claims**: a
README teaching a path that crashes, "proven end-to-end" about two tests
that never touch the shipped path, a docstring describing a guarantee the
test does not provide. Those are defects *in the expectations*, so no
harness catches them; the only reader who can is one who does not already
believe them.

- Review **each unit as it completes**, not in a batch at the end.
  Batching loses the correspondence between finding and reasoning, and by
  then the next change is built on the defect.
- Give the reviewer an **explicit scope** — a commit range, not "the
  current work".

Proven here across seven PRs (#213); three of four reviewed PRs that were
believed finished had defects that would have reached users.

## Decisions needed

Every response ends with a `## Decisions needed` block: numbered, one line
each, **a recommendation per item**, and nothing requiring an answer
anywhere else in the message.

- It is a **running backlog** — anything still unanswered from earlier
  turns is carried forward, not dropped.
- **A decision, once made, never reappears.** Answered items leave the
  block permanently; do not re-list them for confirmation, as a summary,
  or "for completeness". Re-asking a settled question is the same failure
  as burying a live one — it trains the reader to skim the block, which
  is exactly what the block exists to prevent. If a decision genuinely
  needs revisiting because something changed, say what changed and treat
  it as a new item.
- When no decision is genuinely needed, **say so** rather than omitting
  the block; a silently absent block is ambiguous on exactly the turns
  where it matters.
- Only decisions the human genuinely owns. Anything resolvable from the
  code, the request, or a sensible default is the agent's to make —
  otherwise the block becomes noise and gets skimmed like the prose it
  replaced.

The point is separating **reporting** (read at whatever depth you choose)
from **blocking asks** (must not be missed). Prose is good at the first
and structurally bad at the second.
