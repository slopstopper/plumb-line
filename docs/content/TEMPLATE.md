# Content draft — template and gates (release-to-content routine, #255)

One short piece per release or notable merge, drafted from what actually
shipped. Drafts only; the owner approves everything outbound. Shared gates
live on [#260](https://github.com/slopstopper/plumb-line/issues/260); this
file is the per-draft checklist.

## Source material

Draft from artifacts, not memory: the CHANGELOG section for the release, the
release-harness record in `docs/validation-results.md`, the dogfood section
in `docs/dogfood.md`, and the closed milestone's issues. Every claim in the
draft must trace to one of these or to a recorded number.

## Length follows the release

Density follows the version (owner decision, 2026-09-25): a patch is a small
change and gets a short piece. Budgets count the words above the disclosure
rule:

| Release | Budget |
| ------- | ------ |
| patch (`x.y.Z`) | 300 words |
| minor (`0.Y.0`, and `X.Y.0` after 1.0) | 600 words |
| major (`X.0.0`, from 1.0) | 1000 words |

Lead with what changed for a user and why; one paragraph for what the review
and release harness found; skip the per-fix inventory, which the CHANGELOG
already carries. `scripts/test_content_language.py` fails a piece over its
budget. The pieces written before the budget existed are listed there and
kept as dated artifacts.

## The four gates, in order

1. **Audit.** Run `plumb-line-audit` on the draft. Maturity vocabulary
   holds (`current` / `planned`, never aspiration stated as fact); every
   claim traceable to a shipped artifact or a recorded number. Findings are
   fixed before the draft moves on.
2. **Language standard.** Run `python3 scripts/check_content_language.py
   <draft>` and review every flag. The flagger warns, a human decides — a
   flagged line is either rewritten or consciously kept. Banned outright:
   "it is not X, it is Y" constructions and their bare forms ("X, not Y" /
   "not X but Y"), rhetorical triplets, the
   delve/landscape/unlock/game-changer register, "the quiet part", hollow
   superlatives, emoji headers, roll-on emphasis tails. Em dashes are
   counted, not flagged: keep them to a bare minimum. Plain, specific, dry;
   short sentences. The flagger matches per paragraph, so a construction
   split across a hard wrap is seen (the per-physical-line limit found by the
   v0.10.0 dogfood, #316, is closed); a blank line still ends what it joins.
   The 0.9.0 piece carries one flagged construction on purpose — it predates
   the 2026-08-18 bare-contrast ruling and is kept as a dated artifact, pinned
   as exactly that one keep in `scripts/test_content_language.py`.
3. **Disclosure.** The piece ends with the disclosure block, wording
   owner-approved 2026-08-15 (model parenthetical dropped by owner ruling,
   recorded 2026-08-18):

   > *Written by a machine, audited like everything else here.*
   >
   > *Drafted by Claude,*
   > *Reviewed, edited and approved by @effythealien.*
   >
   > *Sources: <artifacts and issues the claims trace to>.*

   The first line is the one sanctioned dry line per piece.
4. **Venue courtesy.** There is no numeric cap (the former 4/month cap was
   removed by owner decision 2026-09-07, recorded on #260: it guarded
   against unsupervised automation this architecture does not have, and it
   wrongly counted the owner's own content). The owner's approval before
   anything leaves is the rate limiter, and owner-made content is never
   counted. What remains: never stack a second submission into the same
   venue or community while one is pending there, and every outbound
   fact-pack passes `plumb-line-audit` first.

## Publishing

Home is this directory: `docs/content/YYYY-MM-DD-<slug>.md`, merged via PR
like anything else. Once the piece merges, put it where readers already look
(one PR / edit each, part of closing the draft-due issue — these three are
rendering the approved piece, not new outbound):

1. **Release notes** — embed the piece in full at the top of the matching
   GitHub release body, above the generated "What's Changed" list
   (`gh release edit <tag> --notes-file …`). Convert the piece's
   repo-relative links to absolute URLs (release bodies do not resolve
   them), and end the embed with a "Canonical copy:" link to the file in
   this directory so the release copy never becomes a second source of
   truth.
2. **Site** — nothing per-piece. `slopstopper/slopstopper.org` generates
   its writing list from this directory (`scripts/sync-writing.mjs`, daily
   and on the release ping), so the merge into `docs/content/` is the
   publish step.
3. **README** — nothing per-piece; the Status section already links this
   directory.

Publishing anywhere beyond these owned surfaces is the owner's manual act,
subject to venue courtesy (gate 4).

## Worked examples

[2026-08-15-plumb-line-0.9.0-the-front-door.md](2026-08-15-plumb-line-0.9.0-the-front-door.md)
— drafted from the v0.9.0 release, taken through all four gates, edited and
approved by the owner. The routine has since run for
[0.10.0](2026-08-19-plumb-line-0.10.0-pay-down-the-ledger.md),
[0.11.0](2026-09-15-plumb-line-0.11.0-honest-over-time.md),
[0.11.1](2026-09-20-plumb-line-0.11.1-measured-nothing.md),
[0.11.2](2026-09-25-plumb-line-0.11.2-the-checkers-own-blind-spot.md) and
[0.11.3](2026-09-25-plumb-line-0.11.3-pages-that-match-the-code.md), the first
written to the length budget.
