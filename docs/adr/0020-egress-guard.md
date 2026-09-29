# ADR-0020: The egress guard refuses at the output point, fails closed, and excludes mock by default

**Status:** Accepted · 2026-09-29 (owner decisions on GH #120)

## Context

`auditMeta` reports an inconsistent or tainted envelope after the fact.
Nothing *stopped* such a value at the point where it leaves the system: an
export, a display, a publish. Principle 4 promises that mock, approximate,
fallback and cached data is "excluded from outputs unless explicitly opted
in", and at run time nothing enforced it. The impossible-task spike showed
the cost (#462, recorded on #123): in the FX task, in 11 of 15 runs that
mocked the provider in the tests, the fake rate flowed through the real code
and came out marked `source: "real"`.

ROADMAP #27 and #120 proposed `require(x, { noMock, minConfidence })`, a
guard that "throws (or returns a typed refusal)". That left four questions
open: the name, the failure shape, the defaults, and what to do with an
envelope that cannot back its own claims.

## Decision

On 2026-09-29 the owner accepted four recommendations, as proposed on #120
and recorded there with the owner's answers ("1. Yes guard", "2. Yes", "3.
Yes", "4. Yes"):

1. **The name is `guard`**, not `require`. In a CommonJS module,
   `const { require } = …` is a syntax error, since `require` is the module
   wrapper's parameter. Anywhere else the name shadows Node's own. (ADR-0019
   refers to the proposal by its old name.)
2. **A refusal throws `ProvenanceRefused`** (a `ValueError` in Python) with a
   `reasons` list; success returns the marked value unchanged, so an output
   point writes `unwrap(guard(x))`. A refusal that can be ignored is not
   enforcement; a display that should show "unavailable" catches it.
3. **`noMock` is on unless turned off** (Principle 4: excluded from outputs
   unless explicitly opted in). `minConfidence` defaults to no floor.
4. **Fail closed.** A value with no envelope, or a malformed one, is always
   refused; taint and confidence are judged from the whole lineage, not the
   headline fields; a bad option is a programmer error, raised as a different
   exception from a refusal.

Applying these decisions, the author settled the following details; they are
normative in SPEC §5c and were refined over two independent reviews:

- **The guard covers Principle 4's mock clause only.** The rest of what P4
  names (fallback and inferred sources, and cached data, which the HTTP
  adapter marks `real`) is not refused; a source floor is #541.
- **A bad option is raised before the value is examined**, so a bad call
  fails the same way whatever it is given.

- **"Malformed"** covers every `validateEnvelope` issue, and also values the
  guard cannot place on the ladders: an off-ladder `source`, `confidence` or
  `weakestSource`, a lineage step that is not a plain object, a step whose
  `source` or `confidence` is off its ladder or whose `derivedFromMock` is
  not a boolean, and a `confidenceScore` that is not a number in `[0, 1]`. The constructors already refuse such values (ADR-0019); the
  law tolerates them in a handed envelope, and an output point does not.
- **An envelope the audit flags is refused**, since it makes a claim it
  cannot back: laundering, over-claiming, dropped taint, an unreproducible
  derivation, a malformed version. The `version-legacy:` and
  `version-future:` advisories are not refusals. §5b says a future version is
  accepted "so that consumers built against an older checker keep working
  against newer producers", and a guard that refused it would stop every
  output of an older consumer the day a producer upgraded. A newer envelope
  that uses a source or confidence rung this library does not know is still
  refused, as malformed: the guard cannot place it.
- **Bad options are a `TypeError` in both languages.** A refusal is a
  `ValueError` in Python, and a bad option never is, so catching one cannot
  swallow the other. An unknown option names itself in both.
- **A step with no `confidence` counts as `none`** against a minimum: the
  guard vouches only for what the lineage states.

The behaviour is pinned for both languages by the `guard` kind in
`primitives/conformance/cases.json`.

## Consequences

- An output point can enforce Principle 4's mock clause in one call, in both
  languages, with identical refusals. Fallback and inferred sources, and
  cached data, are **not** refused: a source floor is a separate, planned
  option (#541).
- Unmarked values are refused. A codebase that guards an output must mark
  what flows into it first. That is the adoption cost, and it is the point:
  an unmarked value has no provenance to vouch for.
- The guard enforces what an envelope says, not whether it is true: an
  envelope fabricated to be internally consistent passes it, as it passes the
  audit (threat model, N3).
- #123's fixture helper ("no taint escape") is planned to reuse this `noMock`
  semantics rather than define its own.
