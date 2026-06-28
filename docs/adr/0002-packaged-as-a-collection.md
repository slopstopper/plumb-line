# ADR-0002: Packaged as a skill collection, not one skill

**Status:** Accepted · 2026-06-28

## Context

The discipline plumb-line carries spans three distinct moments in a project's
life: _learning_ the method, _starting_ a project under it, and _auditing_
existing work against it. These have different triggers, different audiences, and
different actions (one teaches, one installs, one reviews).

We considered packaging this as a single large skill that did everything, versus
a collection of focused skills, versus loose documentation with no skill
surface at all.

A single mega-skill would be triggered ambiguously ("set up" vs "audit" vs
"explain" all collapse into one description), would grow large, and would mix
read-only review logic with file-generating install logic. Loose docs would carry
no enforcement and no trigger affordance.

## Decision

Package plumb-line as a **collection** (a Claude Code plugin) of three focused
skills over a single shared principles document:

- `plumb-line-method` — the umbrella/teaching skill; loads the principles.
- `plumb-line-bootstrap` — starts a project: interview → ruleset → install
  enforcement.
- `plumb-line-audit` — audits a diff/repo against the principles; read-only.

**The philosophy is written exactly once**, in `reference/portable-principles.md`.
The three skills _reference_ it; they never restate it.

## Consequences

- Each skill stays small and has one clear trigger, so the right skill activates
  for the right intent.
- The principles cannot drift between skills, because there is only one copy. A
  change to the discipline is a one-file change.
- Concerns stay separated: `audit` is read-only and never writes; `bootstrap`
  generates and installs config; `method` takes no actions at all.
- The cost is a small amount of cross-referencing machinery (skills must point at
  the principles doc rather than embedding it), and a contributor must resist the
  temptation to inline a principle into a skill for convenience.
