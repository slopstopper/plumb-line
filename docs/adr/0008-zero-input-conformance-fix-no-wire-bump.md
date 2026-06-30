# ADR-0008: Correcting a self-contradicting result is a conformance fix, not a wire-version bump

**Status:** Accepted · 2026-07-01

## Context

`SPEC.md` §1 ("Envelope versioning") states that *changing the combination law's
result for an existing case is a breaking change and MUST bump the version*
(`PROVENANCE_VERSION`). The wire version exists so consumers can pin to a stable
envelope shape and combination behaviour.

The v0.3.1 zero-input fix (issue #25) changes the result of an existing,
conformance-pinned case: `combineProvenance()` with no inputs previously returned
`source: "derived"` with an empty `lineage`. Taken literally, §1 says that change
MUST bump `PROVENANCE_VERSION` 1 → 2.

But the prior result was **internally inconsistent**: SPEC §3 mandated
`source: "derived"` for the zero-input case, while SPEC §5 condition 6 flags any
`derived` value with an empty `lineage` as *unreproducible*. The producer
(`combineProvenance`) was emitting an envelope that the SPEC's own checker
(`auditMeta`) condemns. No conformant consumer could have relied on that output
as correct, because the specification simultaneously declared it unsound.

The v0.3.1 dogfood self-audit surfaced this as a governance contradiction: the
fix is honest (it makes the producer agree with the checker), but the SPEC asserts
a versioning rule the fix appears to violate.

## Decision

Amend `SPEC.md` §1 with an explicit carve-out: changing the combination law's
result for an existing case is a breaking change that MUST bump the wire version
**except** when the prior result violated another normative section of this SPEC.
Correcting such a self-contradiction is a **conformance fix**, not a breaking
change, and MUST NOT bump `PROVENANCE_VERSION`. The exemption is narrow and
guarded: such a fix MUST be recorded (CHANGELOG + this ADR) and pinned by a
conformance case so the corrected behaviour cannot silently regress.

`PROVENANCE_VERSION` therefore stays `1` for v0.3.1, and the release remains a
patch.

## Consequences

- The wire version keeps its meaning: it moves for changes to *valid, relied-upon*
  behaviour, not for corrections to outputs the SPEC already declared unsound. A
  consumer pinned to v1 loses nothing — the old zero-input output was never a
  conformant envelope.
- The exemption is deliberately constrained to *self-contradiction* fixes
  (a result another normative section rejects). A change to a result that was
  internally consistent still bumps the version, no exceptions. This keeps the
  carve-out from becoming a loophole that launders breaking changes as "fixes."
- The guard rails are mandatory: CHANGELOG entry, an ADR, and a conformance case.
  The zero-input fix satisfies all three (CHANGELOG [Unreleased], this ADR, and the
  combine + audit cases in `conformance/cases.json`).
- The SPEC header's parenthetical "(stable — no breaking changes planned)" is
  dropped: predicting the absence of future breaking changes is the kind of
  maturity over-claim the project's own P6 vocabulary forbids. The schema is
  version 1; that is a fact, not a promise.
