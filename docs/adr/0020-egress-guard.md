# ADR-0020: The egress guard refuses at the output point, fails closed, and excludes mock by default

**Status:** Accepted · 2026-09-29 (owner decisions on GH #120)

## Context

`auditMeta` reports an inconsistent or tainted envelope after the fact.
Nothing *stopped* such a value at the point where it leaves the system: an
export, a display, a publish. Principle 4 promises that mock and fallback
data is "excluded from outputs unless explicitly opted in", and at run time
nothing enforced it. The impossible-task spike showed the cost (#462,
recorded on #123): in the FX task, in 11 of 15 runs that mocked the provider
in the tests, the fake rate flowed through the real code and came out marked
`source: "real"`.

ROADMAP #27 and #120 proposed `require(x, { noMock, minConfidence })`, a
guard that "throws (or returns a typed refusal)". That left four questions
open: the name, the failure shape, the defaults, and what to do with an
envelope that cannot back its own claims.

## Decision

On 2026-09-29 the owner accepted all four recommendations, recorded on #120:

1. **The name is `guard`**, not `require`. In a CommonJS module,
   `const { require } = …` is a syntax error, since `require` is the module
   wrapper's parameter. Anywhere else the name shadows Node's own. (ADR-0019
   refers to the proposal by its old name.)
2. **A refusal throws `ProvenanceRefused`** (a `ValueError` in Python) with a
   `reasons` list; success returns the marked value unchanged, so an output
   point writes `unwrap(guard(x))`. A refusal that can be ignored is not
   enforcement; a display that should show "unavailable" catches it.
3. **`noMock` is on unless turned off.** That is Principle 4's own wording:
   excluded unless explicitly opted in. `minConfidence` defaults to no floor.
4. **Fail closed.**
   - A value with no envelope, a malformed envelope (any `validateEnvelope`
     issue), or one the audit flags (any `auditMeta` issue except the
     `version-legacy:` advisory) is refused, whatever the options.
   - Taint and confidence are judged from the lineage as well as the headline
     fields, so a headline the lineage contradicts cannot pass.
   - A bad option is a programmer error of a different type, raised before the
     value is examined, so it is never mistaken for a refusal.

The behaviour is normative in SPEC §5c and pinned for both languages by the
`guard` kind in `primitives/conformance/cases.json`.

## Consequences

- An output point can now enforce P4 in one call, in both languages, with
  identical refusals.
- Unmarked values are refused. A codebase that guards an output must mark
  what flows into it first. That is the adoption cost, and it is the point:
  an unmarked value has no provenance to vouch for.
- Legacy envelopes (no `provenanceVersion`) still pass on their content. An
  envelope from a newer wire version is refused, because the guard cannot
  vouch for semantics it does not know.
- Error types differ by language convention: JS raises `TypeError` for every
  bad option, and Python raises `TypeError` for `no_mock` and an unknown
  keyword but `ValueError` for `min_confidence`. The conformance table pins
  the message prefix, not the type.
- #123's fixture helper ("no taint escape") reuses this `noMock` semantics
  rather than defining its own.
- `guard` checks mock taint and confidence only. A `source` allow-list (for
  example "real only") is not an option; a caller who needs one reads
  `metaOf(x).source` after the guard passes.
