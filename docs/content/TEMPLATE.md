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

## The four gates, in order

1. **Audit.** Run `plumb-line-audit` on the draft. Maturity vocabulary
   holds (`current` / `planned`, never aspiration stated as fact); every
   claim traceable to a shipped artifact or a recorded number. Findings are
   fixed before the draft moves on.
2. **Language standard.** Run `python3 scripts/check_content_language.py
   <draft>` and review every flag. The flagger warns, a human decides — a
   flagged line is either rewritten or consciously kept. Banned outright:
   "it is not X, it is Y" constructions, rhetorical triplets, the
   delve/landscape/unlock/game-changer register, hollow superlatives, emoji
   headers, roll-on emphasis tails. Plain, specific, dry; short sentences.
3. **Disclosure.** The piece ends with the disclosure block, wording
   owner-approved 2026-08-15:

   > *Written by a machine, audited like everything else here.*
   >
   > *Drafted by Claude (<model>),*
   > *Reviewed, edited and approved by @effythealien.*
   >
   > *Sources: <artifacts and issues the claims trace to>.*

   The first line is the one sanctioned dry line per piece.
4. **Cap.** At most 4 published items per month across all routines
   (#255/#256/#257 combined). Count the month's published pieces in
   `docs/content/` (filenames are dated) plus any outbound the owner placed
   elsewhere; if this piece would be the fifth, it waits.

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
2. **Site** — add a dated row to the §writing list on
   `slopstopper/slopstopper.github.io` (static list by design; a row per
   piece, capped at 4/month, cannot rot against an API).
3. **README** — nothing per-piece; the Status section already links this
   directory.

Publishing anywhere beyond these owned surfaces is the owner's manual act
and counts against the cap.

## First worked example

[2026-08-15-plumb-line-0.9.0-the-front-door.md](2026-08-15-plumb-line-0.9.0-the-front-door.md)
— drafted from the v0.9.0 release, taken through all four gates, edited and
approved by the owner.
