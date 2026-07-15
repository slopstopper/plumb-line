# ADR-0010: Wire v2 — batch the schema-breaking changes into one bump

**Status:** Accepted · 2026-07-11

## Context

Three pending changes each require breaking the envelope schema, and
`PROVENANCE_VERSION` is a wire version that exists so consumers can pin to a stable
envelope shape (SPEC §1). The three:

- **#52 — durable step ids.** v0.3.1 made `combineProvenance` concurrency-safe by
  renumbering the whole output lineage per combine. Ids are unique *within* an
  output (SPEC §4) but not stable across recombination — the same upstream step is
  `step-2` in one envelope and `step-4` in another. That is a weak foundation for
  the P8 reproducibility / audit-trail story (diff, dedupe, cross-reference by id).
- **#116 — the `inferred` source.** The ladder
  `unavailable < mock < fallback < semiReal < derived < real` has no seat for an
  LLM/agent-produced value — the dominant source of 2026 — so teams shoehorn it into
  `semiReal`/`fallback` inconsistently. The Agent-epistemic-state track (#128) needs
  a ladder position to point at.
- **#93 — version legibility.** A consumer cannot tell which schema version produced
  an envelope; nothing is embedded.

A wire bump costs more the longer it waits: every release adds v1 envelopes to the
world, raising the eventual migration cost. Historically this bump kept slipping
because it was bundled with more appealing on-ramp features (the v0.7.0 "Lower the
on-ramp" theme) and deferred as a unit. Meanwhile three downstream tracks are gated
on it settling: v0.9.0 "Refuse & explain", "Provenance across boundaries", and
"Agent epistemic state".

## Decision

**Bump `PROVENANCE_VERSION` 1 → 2 exactly once, batching all three changes into the
v0.7.0 release, and split the deterministic on-ramp features (#91, #92, #138, #96,
#24) out to v0.7.1.** The schema becomes the release headline rather than a
passenger; features that do not touch the wire do not share the breaking release.
The ordering is decided by asymmetry: wire v2 blocks three tracks and decays with
time, while the on-ramp work blocks nothing and does not decay — so wire v2 goes
first.

The three schema decisions:

1. **#52 — content-addressed step ids (Merkle).** A step's id is a truncated
   SHA-256 over the step's canonical fields concatenated with the (sorted) ids of
   its input steps. A subtree's hash depends only on that subtree, so combining A
   with B cannot change A's id — ids are stable across recombination. Random
   per-combine UUIDs are **rejected**: they are non-deterministic, cannot be pinned
   in the cross-language conformance table, and any deterministic UUID collapses back
   into content-addressing. A flat field-only hash (no ancestry) is **rejected**: it
   collides distinct steps that merely share fields; including input ids means a
   collision occurs only when content *and* ancestry match — i.e. the same
   derivation — which is intentional dedup.

2. **#116 — add one `inferred` rung**, placed `mock < inferred < fallback`. Because
   `combine` takes the weakest source, this conservative placement makes an
   agent-estimated value drag trust down hard — barely above deliberate test fakery —
   which matches the project premise that agent output is suspect until evidenced. A
   general registered-vocabulary mechanism is **rejected** (YAGNI, and divergent
   per-project vocabularies would erode plumb-line's shared, comparable honesty
   layer).

3. **#93 — embed the version and validate it asymmetrically.** Every envelope
   carries a compact version field; on read, an unknown *future* version passes with
   a warning (forgiving forward), while an absent or older version is accepted but
   marked legacy (honest backward); combine always stamps the current version.
   Strict rejection of unknown versions is **rejected** (it makes forward
   compatibility impossible and would break the cross-service tracks this bump exists
   to unblock). Embed-without-validating is **rejected** (a version nobody checks is
   the decorative honesty the audit skill flags).

`PROVENANCE_VERSION` is moved by hand; `scripts/bump-version.mjs` does not touch it,
because the release version and the wire version move independently (see the
Versioning note in CLAUDE.md). `#99` (bundling the primitive into the plugin) rides
at the tail of the same release, vendoring the settled v2 source.

## Consequences

- **The wire bump happens once.** Batching #52/#93/#116 avoids spending two breaking
  envelopes on changes that could share one. A future ID-format or ladder change
  would still need its own bump — the batch does not pre-authorize later breaks.
- **Splitting features from the schema is the anti-slip mechanism.** The bump kept
  slipping because it hid behind features; making it the headline and moving #91/#92
  to v0.7.1 removes the coupling that enabled deferral. The on-ramp loses nothing by
  going second (it blocks nothing); the schema gains by going first (it unblocks
  three tracks).
- **Parity is the enforcement.** Each of the three changes lands in both languages
  with rows in `conformance/cases.json` in the same change. The content-addressed id
  in particular pins a known input→id vector so cross-language serialization drift
  fails loudly rather than silently diverging.
- **Forward compatibility is now a stated property**, not an accident: v1 consumers
  reading a v2 (or later) envelope degrade to a warning, never a hard failure. The
  cost is that a genuinely incompatible future change cannot rely on old readers
  rejecting it — it must be detected by the consuming logic, not by version refusal.
- **SPEC moves to version 2**: §4 is upgraded to promise cross-envelope id stability
  and dedup semantics, the ladder section gains `inferred`, and a new section
  documents the embedded version and read policy. SPEC §4's prior, weaker guarantee
  (unique-within-output only) is superseded, not merely extended.
- **The release runs the harness.** The diff touches `primitives/`, so
  `docs/release-harness.md` (blind validation + dogfood self-audit) gates the tag; a
  missed planted violation blocks the release.
