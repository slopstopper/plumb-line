# ADR-0006: Build docs stay private; decisions are published

**Status:** Accepted · 2026-06-28

## Context

Building plumb-line produces three kinds of document: rough **design specs**
(what we explored and settled before building), **implementation plans** (the
task-by-task build instructions), and **architecture decisions** (the durable
"why" behind the shape of the project). The build process leans on the first two
heavily — they are scaffolding for a single feature — but they age fast and
expose half-formed thinking, dead options, and process detail that is noise to a
reader of the finished project.

The question is what a published, shared repository should carry. Publishing
everything buries the durable signal under working notes; publishing nothing
leaves contributors no record of _why_ the project is shaped as it is.

## Decision

**Publish the decisions; keep the working notes local.**

- `docs/specs/` and `docs/plans/` are git-ignored — they live on the author's
  disk as working notes and are never published.
- `docs/adr/` _is_ tracked and published. Durable decisions, with their context
  and consequences, are the record contributors get.

This was hardened in the gitignore deliberately (commit `e066d69`, "harden
gitignore and untrack internal build docs").

## Consequences

- The repository stays legible: a reader sees decisions, not the scaffolding that
  produced them.
- Specs and plans, being git-ignored, are **local-only and unbacked** — if the
  author's working copy is lost, they are gone. That is an accepted trade: they
  are disposable scaffolding, and the decision they justified survives in the ADR.
- There is a discipline cost: when a decision is made, it must be _promoted_ from
  the (private) spec into a (public) ADR, or it is effectively undocumented for
  anyone but the author. This ADR set is the first such promotion.
- The pattern is itself reusable by builders adopting plumb-line: keep your
  build-time scaffolding private, record the decisions that outlive it.
