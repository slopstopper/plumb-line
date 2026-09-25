# Opportunity watcher — weekly sweep contract (#256)

**Status: current.** The routine runs as a Claude Code scheduled cloud agent
(weekly), installed outside this repo by design — the schedule definition
points at this file rather than duplicating it, and the evidence it runs is
the digest trail itself. A gap in that trail, not a config file, is how a
dead routine shows.

**Digest destination (owner decision 2026-09-05, migrated 2026-09-07):
digests are filed as issues in the org's private HQ repo (`slopstopper/hq`),
not in this repository.** Digests W33–W37 were transferred there (hq issues
#1–#5; the old plumb-line issue numbers redirect). If filing on the HQ repo
fails for access reasons, file the digest here instead, open with a line
noting the fallback, and the next working session migrates it.

A weekly scheduled cloud agent sweeps for docking points and files one digest
issue with 0–3 *drafted* actions. It proposes; it never executes. Shared
gates live on [#260](https://github.com/slopstopper/plumb-line/issues/260)
and bind every drafted action.

## Sweep targets (the denominator)

Each digest states which of these were swept and which were not — a quiet
week must be distinguishable from a partial sweep. A target limited by a
known environment limit (below) counts as swept, at that limit:

1. **Papers** — new work on execution provenance, taint tracking in agents,
   agent-skill auditing (arXiv, the venues the 2026 wave publishes in).
2. **Listings** — awesome-lists: inclusion opportunities, plus staleness or
   duplicates in existing listings of this project; status of our open
   listing PRs.
3. **GitHub activity** — topics and discussions around agent provenance and
   epistemic honesty; new projects adjacent to the fit map's profiles;
   name-collision neighbours ("plumbline") if confusion appears.
4. **Claude Code community** — threads where the skills or primitives answer
   a question someone actually asked.

## Environment (known limits)

The routine's cloud environment has limits that hold every week. They are
recorded here once so digests stop restating them (owner decision
2026-09-25, after seven digests each repeated the same gap line):

- **No `gh` CLI.** Use the GitHub MCP tools (`mcp__github__*`) for every
  GitHub read and for filing and closing the digest; use WebFetch for pages
  the tools do not cover.
- **Egress-blocked domains:** `arxiv.org`, `export.arxiv.org`,
  `hn.algolia.com`, `news.ycombinator.com` (as of 2026-09-25, unless the
  owner allows them on the environment). While they are blocked, paper and
  Hacker News coverage comes from web-search snippets alone.

A digest's Denominator mentions these limits only when one has changed: a
domain that now resolves, or a new block. It does not count consecutive
runs. Whoever changes the environment updates this list.

## Digest contract

One GitHub issue per run **on `slopstopper/hq`**, titled
`Watcher digest YYYY-'W'WW`, labeled `track:distribution` and `digest` (the
digest-specific label is what the "Open dispositions" search keys on; both
labels exist on the HQ repo). The "Open dispositions" search also runs
against `slopstopper/hq`. Sections:

- **Denominator** — what was swept, what was skipped, and why.
- **Observations** — what changed since the previous digest, with links;
  no action implied. Tracked items that did not move (open listing PRs, the
  known paper corpus, name-collision neighbours already noted) go on one
  `Unchanged:` line, by name, adding its age once it has been unchanged
  for 30 days or more.
- **Drafted actions (0–3)** — each carries the full draft (a reply, a PR
  description, a piece outline) ready for approval, already passed through
  the #260 gates (audit, language standard via
  `scripts/check_content_language.py`, disclosure where the draft is prose
  for publication). An action without a ready draft is an observation, not
  an action.
- **Open dispositions** — prior digests' actions still awaiting a decision,
  and the state of previously approved ones. Search prior digests **open
  and closed**: zero-action digests are closed when filed.
- **Outbound activity this month** — a record of the month's outbound
  items (see *Disposition protocol*: there is no cap).

**A digest reporting nothing is valid** and still gets filed — "no docking
points found this week" over a stated denominator is a result. Digests are
skippable by design: unread digests lose nothing, because every action waits
in its issue until dispositioned.

**Closing.** A digest with zero drafted actions has nothing to disposition,
so the routine closes it in the same run it files it. A digest with actions
stays open until each action is either declined or executed; the working
session that executes or records the last one closes it. A digest filed on
`slopstopper/plumb-line` as the fallback stays open until it is migrated,
whatever its action count, so the migration is not lost. An open `digest`
issue therefore means something is pending: an undecided action, an
approved one not yet executed, a fallback not yet migrated, or a close the
routine failed to make (the next working session closes it).

## Disposition protocol

The owner comments `approve` / `decline` (with edits freely) per action.
Approved actions are executed by the next working session and are signed
honestly as the owner or the project. Declined actions are recorded, not
resurfaced.

There is no numeric outbound cap (removed by owner decision 2026-09-07 —
the approval gate is the rate limiter, and the owner's own content was
never the automation risk the cap guarded against; owner-made content is
never counted). The remaining rate rule is **venue courtesy**: never stack
a second submission into the same venue or community while one is pending
there. Digests report the month's outbound activity as a record, not
against a budget.

## Mechanism

A Claude Code scheduled cloud agent (weekly) whose prompt points at this
file — the contract is versioned here, not in the schedule definition. Its
only writes are filing the digest issue with its labels and, when it drafted
zero actions, closing that same issue. If the routine stops filing
digests, the gap is visible as missing weeks in the issue list.
