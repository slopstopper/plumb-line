# ADR-0001: Domain-neutral by construction

**Status:** Accepted · 2026-06-28

## Context

plumb-line is the portable distillation of a discipline that was developed inside
a specific project — Veska Index, an observation-first research prototype in the
astronomy/astrology-adjacent space. The transferable value is the _way of
building_ (keep layers separate, keep uncertainty visible, never launder
approximate data into clean truth, enforce these by tooling rather than goodwill),
not the domain it came from.

The risk is obvious: a system extracted from one domain tends to drag that
domain's vocabulary and assumptions along with it. If plumb-line shipped with
astronomy terms, default celestial layers, or origin-specific framing, it would
be unusable — and dishonestly marketed — for the data-pipeline, ML, agent, and
decision-support builders it is actually for.

## Decision

**Veska is the origin, never the subject.** No shipped artifact contains domain
vocabulary — no astronomy, celestial, natal, ephemeris, zodiac, or
project-specific terms. Domain specifics appear only in clearly-labelled
_examples_, and the worked examples are deliberately drawn from _unrelated_
domains (a payments-style service in JS, a data/ML-pipeline in Python).

Domain-neutrality is treated as a property to be **proven, not asserted**: the
dogfood fixtures are intentionally non-origin-domain and exist in both supported
languages, so the abstraction is exercised away from its birthplace.

## Consequences

- Every principle had to be lifted off its original domain into an abstract
  statement plus a "find your version" prompt the bootstrap skill asks the
  builder — the principle is general; the answer is the builder's.
- Contributors must keep domain terms out of `skills/`, `reference/`, `adapters/`,
  and `primitives/`. The origin may be _named_ (as here) only to explain
  provenance, never as live vocabulary.
- The cost is indirection: a reader who wants a concrete picture must go to the
  examples rather than the core, and the core copy is necessarily more abstract.
  We accept that in exchange for genuine portability.
- This decision is the root constraint that the other ADRs operate under.
