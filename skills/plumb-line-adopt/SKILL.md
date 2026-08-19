---
name: plumb-line-adopt
description: Use when a builder wonders what plumb-line would do for their codebase or which part to adopt — or when, mid-task, their work shows a fit signal (adding a mock or fallback near a production path, mixing fixture, cached, or LLM/agent-produced data with real data) and visible uncertainty would help. Inspects the repo, routes to the right skills and, where the fit map matches, the right primitive integration. Read-only: recommends and hands off, never edits or installs.
---

# Adopt plumb-line — which part, on what

REQUIRED READING FIRST: `reference/fit-map.md` (plugin root). If this file
cannot be read, stop immediately and report: "Cannot route: `reference/fit-map.md`
is missing or unreadable. Do not recommend from memory — the fit map is the
source of truth for what the primitives are for." Read
`reference/portable-principles.md` only if the conversation needs the
principles named; the fit map is sufficient for routing.

This skill is a concierge for the whole toolkit — the four sibling skills
AND the run-time primitives. Its job is the question the docs cannot answer
for a specific repo: *"what would I use this on, here?"* It recommends only.
It never edits files, installs anything, or scaffolds code; every action
belongs to the skill it hands off to.

## 1. Look — a lightweight, read-only scan

Scan the repository for **routing signals only** (this is not an audit —
do not read whole files; filenames, imports, and greps suffice):

- HTTP ingestion: `requests` / `httpx` / `fetch` / `axios` whose results
  feed computation; caching or retry-with-cache logic.
- Dataframes: `pandas` / `numpy` imports; `fixtures/`, `sample_data/`,
  or demo CSVs loadable by production-adjacent code.
- LLM or agent surface: LLM SDK calls; fallback/canned-response branches;
  agent-generated artifacts consumed downstream.
- Fakery near production paths: mock flags, `USE_MOCK`-style toggles,
  stub data on non-test paths.
- Existing adoption: `plumb-line-provenance` already imported; a ruleset
  file (`AGENTS.md` / `CLAUDE.md`) declaring layers; installed hooks.

**State your denominator.** Say in one line what the scan covered (e.g.
"scanned imports and top-level layout; did not read function bodies") —
a routing recommendation must not imply deeper knowledge than the scan had.

## 2. Ask — at most three questions

Fill only the gaps scanning cannot see. Good questions: what the builder
is actually worried about; whether the mock/fixture data ever reaches
users or stored outputs; whether they want enforcement or just visibility.
Skip any question the scan already answered. If no builder is present to
answer, route from the scan alone and say so.

## 3. Route — both surfaces, explicitly

Always answer both halves, in plain language, assuming no prior reading:

**Skills surface (applies to every repo).** Recommend which of the four to
run and in what order, with one line each on what it produces:

- `plumb-line-method` — first if the builder wants the reasoning; teaches
  the discipline in minutes.
- `plumb-line-audit` — the zero-setup first taste: reviews the diff or
  repo and reports; needs nothing installed.
- `plumb-line-bootstrap` — when they want the discipline wired in
  (ruleset, hooks, boundary checks).
- `plumb-line-remediate` — only after an audit report exists.

**Primitives surface (fit-mapped).** Match the scan + answers against the
fit map's profiles and say which profile matched and *why, citing what was
seen* ("you call OpenAI with a static fallback in `llm/client.py` —
profile 1"). Before showing code, give a one-minute mechanics primer in
plain words — builders hesitate when the envelope feels opaque: `mark`
wraps a value with metadata at the point it enters; `derive` runs the
builder's own function on the plain values and combines the metadata by
law (taint ORs and cannot be cleared, confidence takes the weakest);
`metaOf`/`meta_of` reads it back; `auditMeta`/`audit_meta` checks the
envelope is consistent. Say plainly what this bounds: the library never
computes or modifies a value, so a labeling mistake misdescribes data
but cannot corrupt it, and a forgotten `mark` fails visibly rather than
silently (the fit map's "Worried about using it wrong?" section is the
source). Then show the profile's smallest useful integration
**adapted to the builder's actual code**: their filenames, their variable
names, the right language, and the right adapter (`taggedFetch` /
`tag_requests` / `PlumbDataFrame` / plain `mark`+`derive`) for their
stack. Show the pattern as a suggestion in conversation — never apply it.

**Non-fit is a first-class outcome.** If the repo matches the fit map's
anti-profile, say plainly: "you do not need the primitives" — then still
give the skills-surface answer, and name what future change would revisit
the verdict (the fit map's anti-profile section closes the same way). Do
not soften the no; a wrong-fit adoption costs the builder more than an
honest walk-away.

**Defuse the greenfield misconception.** Builders commonly assume
provenance must be adopted at a project's start and hesitate on an
existing codebase. When that worry appears — or when the repo is clearly
mature — say what the fit map's "Mid-project is the normal case" section
says: envelopes attach at boundaries, the smallest integration is a few
lines at one call site, nothing is retrofitted, and repo-wide enforcement
is a separate, opt-in, later decision.

**Mixed or uncertain fit is stated as such.** If signals are ambiguous,
say what would settle it, with the builder's own code as the test — never
present a guessed fit as a match.

## The routing report is contracted (routing-format: v1)

The audit and remediate siblings emit versioned, checker-validated shapes;
this skill's routing recommendation is a public output and carries one too
(#269, P7 applied to our own output). The contract is deliberately light —
conversational prose stays conversational; five elements are pinned:

```
routing-format: v1
scope:               <the repository routed>
date:                <YYYY-MM-DD>

denominator: <the Step-1 coverage line — what the scan covered and did not>

## Skills surface
<the Step-3 answer: which skills, in what order, one line each>

## Primitives surface
fit: <profile N | anti-profile | no fit | mixed | uncertain> — cited: <what was seen>
<the mechanics primer and adapted integration, or the honest walk-away>

handoff: <the one offered next step> | none (<reason>)
```

The `fit:` verdict comes from that vocabulary only, always with its citation —
a guessed fit presented as a match is exactly what Step 3 forbids, and the
contract makes the omission mechanical to catch. Validate before emitting,
the same earned-verdict rule as the audit skill: when
`scripts/check_report_format.py` is reachable, run it on the report and fix
violations before printing; the `— clean` marker may only follow an actual
execution, and anything that prevents running it is the `not run (<reason>)`
case, stated in the line.

## 4. Hand off — invoke on yes, never apply

End with ONE short offer naming the next step. When the builder accepts,
invoke that skill directly (via the host's skill mechanism) rather than
telling them to go run it:

- Wire it in → `plumb-line-bootstrap`. When the builder's hesitation is
  "I don't want to set this up wrong," say what bootstrap's opt-in
  scaffold actually does: it wires `mark`/`derive` at the call sites the
  builder names, teaches the pattern at the first site rather than
  carpeting the codebase, and finishes with a test asserting the key
  output audits clean, wired into the pre-commit gate — the builder is
  not hand-assembling from a README.
- See what a review finds first → `plumb-line-audit`.
- Understand the method first → `plumb-line-method`.

If the builder declines, or none is present: stop after the routing
report. This skill's output is a recommendation; leaving with only the
recommendation is a valid ending.

## Surfacing mid-task

This skill may fire while the builder is doing something else — writing a
fallback branch, loading a fixture into a pipeline. In that case: be
brief, point at the one matching profile, show the one-line integration
for the code on screen, and offer to continue or get out of the way. Do
not run the full scan-and-interview over an interruption; the full
routing is for when the builder asks for it.
