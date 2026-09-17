# Monthly strategy digest — contract (#257)

**Status: current** from 2026-10-01 (first scheduled run; the August 2026
digest was filed by hand on 2026-09-17, and September's is the routine's
first). The routine runs as a Claude Code scheduled cloud agent on the first
of each month, installed outside this repo by design — the schedule
definition points at this file rather than duplicating it, and the evidence
it runs is the digest trail on `slopstopper/hq`. A dead routine shows as a
missing month in that trail.

The watcher (`WATCHER.md`, weekly) finds docking points. This routine reports
whether the distribution strategy is working, with the noise in every number
stated, so trend-reading stays honest. Shared gates live on
[#260](https://github.com/slopstopper/plumb-line/issues/260) and bind any
drafted action here too.

## Metrics (the denominator — every one reported, every month)

Each metric is reported with its source, its noise caveat, and last month's
value beside this month's. A number that cannot be retrieved is reported as
`not retrievable (<why>)`, never omitted and never estimated.

1. **Structured user conversations held** — the realest current signal.
   Source: [#253](https://github.com/slopstopper/plumb-line/issues/253) and
   its comments (the notes themselves are local and private; count them, do
   not quote them). Caveat: sample size is single digits; a change of one is
   noise.
2. **Inbound from non-owner accounts** — issues, PRs and discussions opened
   on `slopstopper/plumb-line` by anyone other than the owner and dependabot
   in the month. Source: `gh issue list` / `gh pr list` with a `created:`
   range. Caveat: zero is the expected value at this scale; one is a signal
   worth naming.
3. **List and citation inclusions** — merged listing PRs, new mentions.
   Source: the month's watcher digests on `slopstopper/hq` (their
   "Listings" observations and "Outbound activity" sections) plus a web
   search for the project name with the hyphen and the org. Caveat: the
   name collision with unrelated "plumbline" projects; count only exact
   identity.
4. **Marketplace installs** — reported only if the marketplace ever exposes
   a count; until then the line reads `not visible (no install metric
   exposed)` every month, so its absence stays legible.
5. **Stars, forks, watchers** — `gh api repos/slopstopper/plumb-line`, with
   starred-at dates from the stargazers endpoint. Caveat: at this scale,
   trend lines only; a star records one person's interest and says nothing
   about adoption.
6. **npm and PyPI downloads** — npm from
   `https://api.npmjs.org/downloads/point/<YYYY-MM-01>:<YYYY-MM-last>/plumb-line-provenance`;
   PyPI from pypistats if reachable, else `not retrievable`. Caveat, stated
   every time: at this scale downloads are largely mirrors and bots; a fall
   is not churn and a rise is not adoption.

## What moved, what is stale

- **Moved:** releases tagged in the month (`gh release list`), content
  pieces merged to `docs/content/`, listing PRs merged, milestones closed.
- **Stale:** listing PRs open more than 30 days with no maintainer action;
  `track:distribution` issues with no comment in 60 days; any watcher
  drafted action approved but not executed.

## Strategy assumptions re-checked

The distribution strategy is an internal note kept outside this
repository. Its positioning assumptions are restated here so the digest can
test them against the month's evidence; each is answered `held`,
`contradicted (<evidence>)`, or `no evidence either way`:

1. Skills are the front door and the primitives are the differentiated core;
   the primitives' gap is articulation ("when do I need this?"); their
   value has never been shown to be low.
2. The beachhead is Claude Code and agent builders via the marketplace.
3. Automation drafts, the owner approves; every outbound item passes the
   audit gate and the language standard.
4. The name collision with unrelated "plumbline" projects is mitigated by
   consistent use of the full identity; a rename is off the table unless
   confusion is observed.
5. Evidence of value is one verified external user (skills as standing
   practice); every positioning claim is revisable after the 3–5
   structured conversations in #253.

## Digest contract

One GitHub issue per month **on `slopstopper/hq`**, titled
`Strategy digest YYYY-MM`, labelled `track:distribution` and `digest`, filed
on the first of the following month. Sections, in order:

- **Denominator** — which metrics were retrieved, which were not, and why.
- **Metrics** — the six above, this month beside last month, caveat on each
  line.
- **Moved / stale** — as defined above.
- **Assumptions** — the five above, each with its verdict and the evidence.
- **Drafted actions (0–3)** — only if a metric or a contradicted assumption
  implies one; each a complete draft that has passed the #260 gates. Zero
  is the expected count most months.

**A digest reporting "nothing moved" is valid** and still gets filed. If
filing on `slopstopper/hq` fails for access reasons, file on
`slopstopper/plumb-line` instead, open with a line noting the fallback, and
the next working session migrates it.

## Disposition protocol

The owner comments `approve` / `decline` per drafted action, as for the
watcher. Approved actions are executed by the next working session. The
digest itself needs no disposition; it is a record.

## Mechanism

A Claude Code scheduled cloud agent (monthly, first of the month, 08:00 UTC)
whose prompt points at this file; the contract is versioned here and the
schedule definition only references it. The agent has read access to `slopstopper/plumb-line`
and `slopstopper/hq` and performs exactly one write: the digest issue and its
labels. It proposes; it never executes.
