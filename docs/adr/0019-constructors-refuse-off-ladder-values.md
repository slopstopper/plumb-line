# ADR-0019: Constructors refuse a source or confidence off its ladder; handed envelopes stay tolerated

**Status:** Accepted · 2026-09-28 (owner decision on GH #443)

## Context

`mark(1, { source: "mock", confidence: 0 })` built an envelope whose
`confidence` is not a rung of the certainty ladder. The remediate skill had
taught agents to write exactly that (found by the 2026-09-25 staleness
sweep). Nothing objected:
- `auditMeta` returned no issue.
- The combination law read the unknown rung as `none`, the weakest (SPEC §2).
- Only `validateEnvelope`, a separate opt-in check, noticed, and only because
  `0` is not a string. `confidence: "HIGH"` passed both checkers.

The same gap existed for `source` against the status ladder. A numeric
certainty has a home, `confidenceScore`; the rung is the ordinal the law
propagates.

The two options on #443:
- **Reject at construction.** `makeMeta` / `make_meta`, and everything built
  on them, refuse an off-ladder value. This breaks any caller passing a
  number today.
- **Flag in `auditMeta`.** Keep constructing, and add a logical-consistency
  issue for an off-ladder value.

## Decision

**Reject at construction**, for `source` and `confidence` alike. On
2026-09-28 the owner accepted the recommendation to reject at `mark()`,
recorded on #443. The 2026-09-25 scheduling comment on #443 had already
leaned that way, since a minor can carry the breaking choice. The
recommendation's reasons:
- #120's `require(x, { minConfidence })` compares rungs, so it needs a closed
  ladder. That is why this was decided before #120.
- A value the law cannot place honestly should not be constructible.

- `makeMeta` / `make_meta` throw (JS `Error`) or raise (Python `ValueError`)
  when `source` is not in `STATUS` or `confidence` is not in `CONFIDENCE`.
  That covers `mark` and a `derive` override, which build on them.
- `source` is checked first. Both languages' messages start
  `source must be one of <ladder>` or `confidence must be one of <ladder>`.
  The quoted value after "got" is each language's JSON rendering and may
  differ in form.
- In Python, `None` is refused, not defaulted, matching JS `null`. Omitting
  the argument gives the default, as JS `undefined` does.
- **The refusal is scoped to construction.** Envelopes an implementation is
  handed, such as parsed JSON or another producer's output, are not refused:
  the combination law and the checkers keep reading unknown values as SPEC
  §2 defines. Otherwise one foreign envelope with a stray rung would make
  `combineProvenance` throw where it now degrades honestly to `none`.
- **Pinned by conformance.** A fourth `cases.json` kind, `construct`, holds
  what the constructor accepts and refuses. A `combine` row pins that a
  handed off-ladder envelope still combines.

## Consequences

- **No wire bump.** No envelope field, type or combination result changes,
  only what a constructor will build (SPEC §1, "Envelope versioning"). The
  case table stays at version 1. An implementation built to the old table
  fails on the unknown kind rather than passing silently (#369). But "conforms
  to envelope schema version 2" now asks more at the same version, so a port
  certified before v0.12.0 must re-run. The CHANGELOG and the conformance
  README say so.
- **Breaking for callers** that pass a number, a wrong-case rung, `null` or
  `None`, or an unknown source. A minor carries it under the pre-1.0 rule.
  The fix is to put the number in `confidenceScore`.
- **The audit is unchanged.** It still ignores an unknown rung in a handed
  envelope for its over-claim comparison. Whether it should also flag one is
  a separate question, not decided here.
- #177 (`source` required on leaf constructors) builds on this refusal path.
  When it lands, "omitting the argument gives the default" above stops being
  true for `source`, and #177's ADR amendment says so.

## Alternatives considered

- **Flag in `auditMeta` only.** Not chosen: the owner accepted the
  recommendation to refuse. The recommendation's reasoning was that an
  advisory the builder never runs protects no one, since the case that
  prompted this came from an agent following a skill. It also leaves #120's
  `minConfidence` comparing against an open ladder.
- **Refuse everywhere, including handed envelopes.** Rejected. SPEC §2
  defines how the law reads an unknown value, and §5 requires the checkers to
  be total. Refusing handed envelopes would contradict both, and would turn
  one stray rung upstream into a crash downstream.

## Amendments

- **2026-09-28 (#177).** *Decided by the owner, recorded on the issue:*
  leaf constructors require `source`, with no default. `mark`,
  `make_meta` / `makeMeta`, `PlumbDataFrame` and `PlumbArray` raise when
  `source` is omitted, in both languages, with `cases.json` rows; the break
  is carried by the v0.12.0 minor and named in the CHANGELOG. The reason
  recorded there: the default `derived` goes because a leaf with no parents
  is not derived from anything (such an envelope audited as
  `unreproducible`). So the Decision's "Omitting the argument gives the
  default, as JS `undefined` does" stops being true for `source`; it still
  holds for `confidence`, which defaults to `none`.

  *Implementation choices, made in the PR, not by the owner:*
  - Both languages refuse with the same message,
    `source is required (one of <the status ladder, comma-separated>)`: JS
    throws an `Error`, Python raises `ValueError`.
  - Python uses a private sentinel default rather than a bare required
    parameter, so that leaving `source` out raises the same `ValueError` as
    every other refusal instead of a `TypeError`.
  - `derive` is not a leaf, so the rule does not reach it (SPEC §2). In JS,
    an override of `source: undefined` counts as no override, so its source
    still comes from the combination law.
  - Pinned by three `construct` rows in `cases.json`.

  Recorded here rather than by editing the Decision, because this record is
  append-only.
