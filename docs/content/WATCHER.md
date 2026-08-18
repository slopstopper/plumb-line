# Opportunity watcher — weekly sweep contract (#256)

A weekly scheduled cloud agent sweeps for docking points and files one digest
issue with 0–3 *drafted* actions. It proposes; it never executes. Shared
gates live on [#260](https://github.com/slopstopper/plumb-line/issues/260)
and bind every drafted action.

## Sweep targets (the denominator)

Each digest states which of these were swept and which were not — a quiet
week must be distinguishable from a partial sweep:

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

## Digest contract

One GitHub issue per run, titled `Watcher digest YYYY-'W'WW`, labeled
`track:distribution` and `digest` (the digest-specific label is what the
"Open dispositions" search keys on). Sections:

- **Denominator** — what was swept, what was skipped, and why.
- **Observations** — findings with links; no action implied.
- **Drafted actions (0–3)** — each carries the full draft (a reply, a PR
  description, a piece outline) ready for approval, already passed through
  the #260 gates (audit, language standard via
  `scripts/check_content_language.py`, disclosure where the draft is prose
  for publication). An action without a ready draft is an observation, not
  an action.
- **Open dispositions** — prior digests' actions still awaiting a decision,
  and the state of previously approved ones.

**A digest reporting nothing is valid** and still gets filed — "no docking
points found this week" over a stated denominator is a result. Digests are
skippable by design: unread digests lose nothing, because every action waits
in its issue until dispositioned.

## Disposition protocol

The owner comments `approve` / `decline` (with edits freely) per action.
Approved actions are executed by the next working session, count against the
≤4/month outbound cap, and are signed honestly as the owner or the project.
Declined actions are recorded, not resurfaced.

## Mechanism

A Claude Code scheduled cloud agent (weekly) whose prompt points at this
file — the contract is versioned here, not in the schedule definition. If
the routine stops filing digests, the gap is visible as missing weeks in
the issue list.
