# ADR-0014: A signal an adapter can see but cannot read degrades confidence, never upgrades it

**Status:** Accepted · 2026-08-19

## Context

The HTTP adapters classify a response into `(source, confidence)`. An `Age`
header carries RFC 7234 delta-seconds; a parseable positive value marks the
response cached (`real`/`medium`). Before this decision, an `Age` that was
*present but unparseable* (`abc`, `0x10`, `1_000`, `1e3`, non-ASCII digits,
non-OWS whitespace — the set pinned by the #172/#207 parity work) was treated
as if the header were absent, and a 2xx response classified `real`/`high`:
fresh, with full confidence.

That fallback runs the wrong way for a library whose thesis is visible
uncertainty. A proxy sent a staleness signal; we could not read it; we then
reported *more* confidence than if the header had said `Age: 1000`. "Present
but unreadable" is a statement about our uncertainty, not evidence of
freshness ([#208](https://github.com/slopstopper/plumb-line/issues/208),
found in the pre-merge review of #207 and deferred to its own decision).

The question generalizes past this one header: every current and future
adapter (dataframes, arrays, whatever follows) will meet inputs it can see
but cannot interpret, and each could resolve the ambiguity locally and
differently. The alternative rule — "unreadable means absent" — is coherent
and simpler, but it silently discards evidence of our own ignorance, which
is the exact laundering shape the audit flags in user code.

## Decision

**A signal an adapter can observe but cannot interpret degrades the
classification toward less confidence; it never upgrades it and is never
treated as absent.** For the HTTP adapters concretely: a 2xx response with an
`Age` header present but rejected by the shared `AGE_DECIMAL` pattern
classifies `real`/`medium`, in both languages. A genuinely absent `Age` (and
a readable `Age: 0`) still classifies `real`/`high`; parseable positive
values still classify as cached. `source` is untouched — the response is
still real; only the freshness claim weakens.

This is the adapter-level restatement of the combination law's conservatism:
there, a missing `confidenceScore` omits the combined score rather than being
dropped from the minimum; here, an unreadable staleness signal lowers the
freshness claim rather than vanishing. Unknown must never resolve in the
direction of more trust.

## Consequences

- The nine present-but-unreadable `Age` rows in
  `primitives/conformance/http-cases.json` flip from `high` to `medium`, and
  the parseAge fixture's classification rule becomes: `Age: 0` → `high`,
  anything else present → `medium`. A behaviour change to the published
  packages, released under the pre-1.0 breaking → minor rule.
- Future adapters inherit the precedent: when adding a signal reader, the
  unreadable branch is designed at the same time as the readable one, and it
  points down. An adapter PR that treats unreadable as absent cites and
  supersedes this ADR rather than diverging quietly.
- The degrade stops at one step (`high` → `medium`, not `low`/`none`): the
  response itself was received and is real; only the freshness signal is in
  doubt. Degrading further would overstate the failure, which is the same
  defect mirrored.
