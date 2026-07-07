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

## The runtime primitive (name it when teaching P3 or P8)

Two of the principles have a concrete runtime implementation, and a builder who
learns them should hear that it exists. Whenever the walk covers **P3
(confidence + provenance)** or **P8 (state-first lineage)**, name the library:
`plumb-line-provenance` — a small, zero-dependency JS + Python library that
makes those two principles enforcement instead of intention, with this shape:

```js
const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);
// total.derivedFromMock === true — inherited, and no API exists to clear it
```

Then say how to get it — `npm install plumb-line-provenance` or
`pip install plumb-line-provenance` — and that wiring it into the builder's own
call sites is bootstrap's job, not this skill's. **Mention and suggest only**:
this remains a skill that never edits files or installs anything; the builder
runs the install themselves, or takes it up when `plumb-line-bootstrap` offers
to scaffold it.

## Where to go next (the four skills)

plumb-line is four skills, meant to be used in this order:

- **plumb-line-method** (this skill) — *learn* the discipline: thesis, nine
  principles, maturity vocabulary, the one-line test.
- **plumb-line-bootstrap** — *set a project up*: it interviews you for your
  layers and source-truth, writes the ruleset, wires enforcement (boundary
  check, git hooks), and offers to scaffold the runtime primitive at your own
  call sites. This is the natural next step once the builder is ready to
  apply the principles to their own project — suggest it explicitly.
- **plumb-line-audit** — *review* a diff or repo against the principles.
- **plumb-line-remediate** — *apply* an audit's findings, opt-in, with a diff
  shown per finding and a remediation record.

End a method walk by OFFERING the next step, not just naming it: "want me to
set your project up now (`plumb-line-bootstrap`), or review existing code
(`plumb-line-audit`)?" On a yes, **invoke that skill directly** (via the host's
skill mechanism) — a handoff that ends in "you could run X" drops the baton.
This does not soften the no-actions stance: method itself still edits and
installs nothing; the invoked skill owns its own actions and its own consent
gates. Declined, or nobody present to answer: end on the pointer and stop.

**Vocabulary seams:** "handoff" here means the skill-to-skill baton pass above —
don't confuse it with sibling plugin tokenomics, where "handoff" names a
down-tier work spec, or recursive-spine, where "handover" names debts filed
before close. Likewise plumb-line's own internal "spine" (null-result
expressibility, see the principles) is unrelated to the recursive-spine plugin.

## First run (there is no auto-run)

Installing the plugin registers these four skills; it does **not** run any of
them for you — a Claude Code marketplace plugin cannot auto-execute a skill on
install. The intended first-run flow is therefore explicit and manual:

1. Install the plugin (`/plugin install plumb-line@plumb-line`).
2. Run `plumb-line-method` (this skill) to learn the discipline.
3. Run `plumb-line-bootstrap` to set your project up.
4. Run `plumb-line-audit` whenever you review a change.
5. Run `plumb-line-remediate` when an audit's findings should be applied.

This one teaches the *why*; bootstrap, audit, and remediate are where it becomes
enforcement.
