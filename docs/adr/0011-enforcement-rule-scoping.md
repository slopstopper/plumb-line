# ADR-0011: Output-tag enforcement is scoped to a declared surface

**Status:** Accepted · 2026-07-12

## Context

The provenance primitive has always been **opt-in**: a developer calls
`mark`/`derive`, and the runtime law and `auditMeta` do the rest. Nothing forces a
value-producing function to tag its output — `const r = a.value + b.value` bypasses
taint entirely, and `plumb-line-audit` catches this only probabilistically at review
(ROADMAP #1 / #91). The on-ramp goal is to **invert this to opt-out**: forgetting to
tag a trust-bearing output should be a mechanical error, not something a human must
spot.

The tension is a standing project guarantee. The existing static rule
(`no-provenance-bypass`, PB1–PB4) is **contractually zero-false-positive** — it fires
only at resolved primitive call sites on literal field values, and stays silent on
anything it cannot prove (threat-model N4, SECURITY.md §2, ADR-0004). A rule that
flags *untagged outputs* is categorically broader: naively, it flags every helper
that returns a number. Coverage and trustworthiness trade against each other, and
this project has consistently bought trustworthiness — a lint that cries wolf gets
blanket-disabled and then catches nothing.

Three scoping models were on the table:

- **Heuristic whole-file** — flag every exported function whose return isn't a
  `mark`/`derive`. Maximal coverage, zero config, but breaks the zero-FP contract
  hard (every `toLowerCase()` slug helper fires) and directly contradicts the
  published guarantee. The predictable response is `// eslint-disable` spam, which
  hides real problems too.
- **Annotation opt-in** — check only functions a developer tags
  (`@provenance-required` / a decorator). Purest zero-FP, but it is still opt-**in**
  per function: forgetting the annotation is the same failure mode we have today,
  just with nicer syntax. It barely delivers the invert-the-default goal.
- **Declared-surface opt-out** — the developer declares a *surface* once (file globs
  / a module list, reusing the #29 injection path); inside it, every function is
  checked by default; outside it the rule is a no-op.

## Decision

Adopt **declared-surface opt-out** for output-tag enforcement, shipped as a new,
separate rule (`require-provenance-output`) in each language rather than an extension
of `no-provenance-bypass` — the two have opposite triggers (bad-pattern-present vs
good-pattern-absent) and different config surfaces, so keeping them separate keeps
each rule's contract clean.

Two sub-decisions define the contract:

1. **Opt-in once at the boundary, opt-out per function.** The rule is silent outside
   the declared surface. With no surface configured it is a no-op, so existing users
   are unaffected. The developer draws the boundary; the tool trusts that boundary
   instead of guessing which code is trust-bearing.

2. **Intraprocedural local variable-tracking, silent on the unclassifiable.** Inside
   a watched function, a return is flagged only when it can be *proven* raw —
   raw-computed directly, or through a local holding a raw value. A return of a
   tracked `mark`/`derive` call (directly or via a local) is accepted. A return of
   anything unclassifiable — a parameter, an unknown call — stays **silent**, because
   proving it untagged would require cross-file dataflow the rule deliberately does
   not do. This is what preserves the zero-false-positive contract while still
   catching the common `const t = x * r; return t` miss.

This makes the rule **opt-out where it matters** (inside the vault) without ever
extending the zero-FP guarantee past what local analysis can prove.

## Consequences

- **The zero-false-positive contract survives.** A flag inside a declared surface is
  almost always a real miss, because the developer asserted that surface is
  trust-bearing and the rule only fires on provably-raw returns. The published
  guarantee (N4, SECURITY.md) holds unchanged.
- **The rule does nothing until configured.** Teams that install and walk away get no
  new enforcement; the on-ramp is lowered for teams that take one setup step. This is
  an accepted cost of buying zero-FP over blanket coverage.
- **Coverage is bounded by intraprocedural analysis.** Cross-file flows and
  returned-parameter pass-throughs are silent by design (§Decision 2). Under-claiming
  is the chosen failure direction, consistent with ADR-0004 and the PB1–PB4 rule.
- **Sets precedent for future enforcement rules.** "Declare the surface, enforce
  opt-out within it, stay silent on the unprovable" is now the pattern any later
  enforcement rule should follow, rather than each rule re-litigating the
  coverage/false-positive trade.
- **Rejected alternatives are on record.** Heuristic whole-file (breaks zero-FP) and
  annotation opt-in (barely inverts the default) are documented here so they are not
  reconsidered from scratch.
- **No wire impact.** This is a static-layer decision; `PROVENANCE_VERSION` is
  untouched.
