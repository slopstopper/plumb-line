# ADR-0009: The checker is total on non-object input, with cross-language parity — a conformance fix, not a wire bump

**Status:** Accepted · 2026-07-02

## Context

`SPEC.md` §5 requires the runtime checker (`auditMeta` / `audit_meta`) be
**total**: it returns a list of issue strings and never throws, for *any* input.
Before v0.4.1 the two implementations diverged on non-object input:

- **Python** `audit_meta` guarded only `if meta is None`. A falsy-but-not-`None`
  scalar (`0`, `''`, `False`) — or any other non-dict — fell through to
  `meta.get(...)` and raised `AttributeError`: a §5 totality violation, surfaced
  by the v0.4.0 release-harness dogfood ([#80](https://github.com/effythealien/plumb-line/issues/80)).
- **JS** `auditMeta` guarded `if (!meta)`. That catches falsy input, but a
  *truthy* non-object (a string, a number, an array) fell through and returned
  `[]` — reporting a non-envelope as a clean, consistent envelope.

So for identical non-object input the two checkers could crash (Python) or
silently bless garbage (JS). That is a divergence in the project's central
invariant (JS/Python parity) and, for Python, a totality violation. Neither
behaviour was pinned by a conformance case, so the divergence was invisible to
the parity gate.

## Decision

The checker treats **any input that is not a plain object/dict** — `null`/`None`,
falsy scalars (`0`, `''`, `False`), and truthy non-objects (strings, numbers,
arrays) — as `["missing meta"]`, identically in both languages, and never throws.
An empty object/dict `{}` remains a valid (clean) envelope.

- Python: `if not isinstance(meta, dict): return ['missing meta']`.
- JS: `if (!meta || typeof meta !== "object" || Array.isArray(meta)) return ["missing meta"]`
  (arrays are `typeof "object"` in JS, so they are excluded explicitly).

This is a **conformance fix, not a wire-version bump.** The checker's handling of
*non-envelope* input is not part of the envelope wire format or the combination
law that `PROVENANCE_VERSION` governs; no valid, relied-upon envelope changes
result. `PROVENANCE_VERSION` stays `1` and the release is a patch. Per the
ADR-0008 discipline, the corrected behaviour is guarded: recorded here and in the
CHANGELOG, and pinned by conformance cases (a falsy scalar `0`, a truthy string,
and an array) so it cannot regress.

## Consequences

- **Parity holds across the entire wire domain.** For every input the JSON
  conformance format can encode, `auditMeta` and `audit_meta` now return
  identical results, and the parity gate (`conformance/report.mjs`) enforces it.
- **One residual, out of the wire contract, tracked not hidden.** A
  non-JSON-serializable *object* — a `Map`, `Date`, or class instance — is
  `typeof "object"` and not an array, so JS falls through (returns `[]`) while
  Python's `isinstance(dict)` rejects it (`["missing meta"]`). This edge cannot be
  encoded in `cases.json` (JSON has no such literals), so it is not covered by the
  parity gate; it is tracked as
  [#96](https://github.com/effythealien/plumb-line/issues/96) (`audit-deferral`)
  rather than silently accepted. Both implementations remain total on it.
- **The narrow carve-out of ADR-0008 is preserved.** This decision does not touch
  valid-envelope behaviour; it defines only the checker's response to inputs
  *outside* the envelope contract, which §5's totality requirement already
  demanded be handled without throwing. It is not a lever for laundering breaking
  changes as "fixes."
