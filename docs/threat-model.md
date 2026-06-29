# plumb-line — Trust & Threat Model

This document states what the provenance envelope guarantees, what it
deliberately does not, and against whom. It is the security framing for the
normative law in [`primitives/SPEC.md`](../primitives/SPEC.md); the SPEC defines
*what the envelope is*, this defines *what it is worth trusting against*.

The project's own discipline forbids overstating maturity, so this model is
written to be honest about its non-guarantees — they are listed as prominently as
the guarantees, because a security tool that oversells itself is violating the
exact rule it enforces.

---

## 1. What we are protecting

The asset is the **truthfulness of a value's trust claim**: its `source`,
`confidence`, `derivedFromMock` taint, and `lineage`. The property worth
defending is *conservatism* — a value must never advertise more trust than its
inputs justify. Concretely:

> Once any input is touched by mock or low-confidence data, every value derived
> from it inherits that taint, and no path through the public API silently clears
> the flag.

A break is any way to end up holding an envelope that **claims clean over dirty
ancestry** — laundering, over-claiming, or a dropped taint.

## 2. Who we defend against

| Actor | In scope? | How they are served |
| --- | --- | --- |
| **The honest-but-careless developer** — the primary actor. Wants correct provenance, will make mistakes: combine values by hand, relabel a derived value, forget that a fallback tainted the result. | **Yes — the whole point.** | The combination law makes the right thing automatic; the audit catches inconsistent envelopes at run time; the static lint catches bypass patterns at review time. |
| **The reviewer** auditing a diff before it lands. | **Yes.** | The static lint (PB1–PB4) and the `plumb-line-audit` skill surface laundering and bypass patterns in source. |
| **A malicious actor with code execution in your process / language.** | **No — explicit non-goal.** | They can already do anything: mutate a Python dict, reflectively defeat a freeze, fabricate an envelope. The envelope is integrity *evidence*, not a sandbox. See §4. |

The envelope is a discipline against self-deception and accident, not a security
boundary against an adversary who already runs code beside it.

## 3. Guarantees

These hold through the documented public API (`mark`, `derive`,
`makeMeta`/`make_meta`, `unwrap`, `auditMeta`/`audit_meta`):

- **G1 — Taint cannot be cleared.** `derivedFromMock` is the logical OR over all
  inputs, computed *before* any override is applied. `derive`'s `metaOverride`
  whitelist cannot reach it, and the static lint flags a literal attempt (PB1–PB3).
  This is the one hard law (SPEC §3 rule 1).
- **G2 — The law is conservative and order-independent.** Combined `confidence`
  is the weakest input; `confidenceScore` is the min only when *every* input has
  one (a gap omits it); `source` is fixed to `"derived"` and never promoted
  (SPEC §3).
- **G3 — The audit is never laxer than the law.** `auditMeta` treats an
  out-of-enum lineage confidence as the `none` floor — the same way the law
  does — so a bogus value can't slip a later over-claim past the checker. The
  audit is total: malformed input yields an issue list, never an exception
  (SPEC §5). *(Hardened — see Changelog F1.)*
- **G4 — `derive` is no weaker than the constructor.** Overrides are routed
  through `makeMeta`, so an out-of-range `confidenceScore` (or unrankable
  `weakestSource`) is dropped by the same validation rather than stored raw and
  silently skipping a downstream check. *(Hardened — see Changelog F2.)*
- **G5 — An envelope owns its lineage.** Each meta receives a **copy** of every
  lineage step, so two envelopes that share ancestry no longer share mutable step
  objects; tampering with one cannot retroactively rewrite another's recorded
  history. *(Hardened — see Changelog F3.)*

## 4. Non-guarantees (read these)

- **N1 — Python envelopes are tamper-*evident*, not tamper-*proof*.** Python has
  no cheap deep-freeze, so envelopes and lineage steps remain plain mutable
  dicts. A caller *can* edit a dict it holds. What it *cannot* do is have that
  edit leak into a sibling envelope (G5), and any resulting inconsistency is
  detectable by `audit_meta`. The JavaScript build goes further: `mark` /
  `derive` results, their meta, the lineage array, and each step are
  `Object.freeze`d, so in-process tampering throws in strict mode. **This
  asymmetry is intentional and language-honest** — do not assume Python parity on
  immutability.
- **N2 — `unwrap` returns the live payload by reference.** Mutating the
  unwrapped value mutates the wrapped one. This is expected semantics (it is the
  payload, not the envelope), but it means the *value* is not deep-frozen even in
  JS — only its provenance metadata is.
- **N3 — Fabricated envelopes are not prevented, they are detected.** Nothing
  stops code from hand-building `{ source: "real", derivedFromMock: true, … }`.
  That is precisely the inconsistency `auditMeta` reports (laundering) and the
  lint flags at the call site. Defense is *detection in depth*, not prevention at
  construction.
- **N4 — The static lint is deliberately incomplete.** It is contractually
  zero-false-positive: it fires only at resolved primitive call sites on literal
  field values. Patterns that need whole-program dataflow to judge (e.g. a bare
  `x.value` that may or may not hold a marked value) are out of scope for
  envelope schema version 1 (SPEC §6). Under-claiming is a design choice, not a
  gap to be reported as a false negative — though novel *literal* bypasses within
  scope are in scope for §2 of [`SECURITY.md`](../SECURITY.md).

## 5. Defense in depth

The same discipline is enforced at three points, so a miss at one is caught at
another:

1. **Construction (run time)** — the combination law in `primitives/` makes the
   conservative result the default; you have to actively override to lie.
2. **Inspection (run time)** — `auditMeta` / `audit_meta` re-derives the
   consistency conditions from the envelope and reports any that fail, catching
   hand-built or tampered metas (N3).
3. **Review (static)** — the `no-provenance-bypass` ESLint rule and
   `provenance_lint.py` flag the four bypass patterns (PB1–PB4) in source before
   the code runs, and the `plumb-line-audit` skill reviews a diff against the
   principles.

A determined in-process attacker (§2) defeats all three; an accident or an
oversight is stopped by at least one.

## 6. Hardening changelog

Findings from security review, with the guarantee each one restored.

| ID | Issue | Resolution | Restored |
| --- | --- | --- | --- |
| **F1** | `auditMeta` filtered out-of-enum lineage confidences *before* finding the weakest, so a bogus confidence let a later high claim pass clean — the checker was laxer than the law. | Unknown lineage confidences map to the `none` floor (mirroring `weakestConfidence`); genuinely-absent confidences stay skipped (no false positives). | G3 |
| **F2** | `derive` copied overrides in raw, bypassing the validation `makeMeta` enforces; an out-of-range `confidenceScore` was stored and then silently no-op'd the numeric over-claim check. | `derive` routes overrides through `makeMeta`; taint is still force-OR'd first (G1 intact). | G4 |
| **F3** | Envelopes and lineage steps were mutable and shared by reference across parent/child metas, so editing one meta's history rewrote every sibling sharing that step. | `makeMeta` clones each lineage step; JS additionally freezes steps, the array, the meta, and the envelope. | G5 |
| **F4** | The G3 totality clause was unmet in Python: `audit_meta` read each lineage step with an unguarded `s.get(...)`, so a malformed step (`None`, a bare string) raised `AttributeError` instead of returning an issue list — and JS, using `s?.field`, did not. | `audit_meta` reads fields through a dict-only `steps` view (non-dict steps count as no-signal), keeping the raw `lineage` only for the length check — matching JS exactly. | G3 |

F1–F3 have a regression test in `primitives/{js,python}` labelled with their ID;
F4 was JS-total already, so its regression test lives in `primitives/python`.

---

*This model covers the provenance primitive and its enforcement adapters. The
skills (`plumb-line-method`, `-bootstrap`, `-audit`) are read-only or generative
and carry no runtime trust boundary of their own.*
