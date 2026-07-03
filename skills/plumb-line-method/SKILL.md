---
name: plumb-line-method
description: Use when a builder wants to learn or be reminded of the plumb-line method — the discipline of epistemic honesty enforced by tooling. Teaches the thesis, the nine portable principles, the maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.
---

# The plumb-line method

Read `reference/portable-principles.md` (relative to the plugin root) and teach
from it. Do not restate the principles here — that file is the single source.
If the file cannot be read, stop immediately and report: "Cannot teach: `reference/portable-principles.md` is missing or unreadable. Do not continue from memory."

When invoked:

1. Read the principles document.
2. Give the builder the thesis and the spine (null results are valid) first.
3. Walk the nine principles only as deep as asked; lead with the one most
   relevant to what the builder is doing.
4. Always end on the one-line test as the portable gut-check.
5. Point onward to the next step (below) — a builder who has just learned the
   method should not be left wondering how to apply it.

This skill never edits files or installs anything.

## Where to go next (the three skills)

plumb-line is three skills, meant to be used in this order:

- **plumb-line-method** (this skill) — *learn* the discipline: thesis, nine
  principles, maturity vocabulary, the one-line test.
- **plumb-line-bootstrap** — *set a project up*: it interviews you for your
  layers and source-truth, writes the ruleset, and wires enforcement (boundary
  check, git hooks). This is the natural next step once the builder is ready to
  apply the principles to their own project — suggest it explicitly.
- **plumb-line-audit** — *review* a diff or repo against the principles.

End a method walk by naming the next step: "to apply this to your project, run
`plumb-line-bootstrap`; to review existing code, `plumb-line-audit`."

## First run (there is no auto-run)

Installing the plugin registers these three skills; it does **not** run any of
them for you — a Claude Code marketplace plugin cannot auto-execute a skill on
install. The intended first-run flow is therefore explicit and manual:

1. Install the plugin (`/plugin install plumb-line@plumb-line`).
2. Run `plumb-line-method` (this skill) to learn the discipline.
3. Run `plumb-line-bootstrap` to set your project up.
4. Run `plumb-line-audit` whenever you review a change.

This one teaches the *why*; bootstrap and audit are where it becomes enforcement.
