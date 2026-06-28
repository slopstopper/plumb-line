# ADR-0005: Provenance primitive — one law, two layers

**Status:** Accepted · 2026-06-28

## Context

plumb-line's principles include confidence + provenance, quarantined fakery, and
state-first lineage — "never launder mock/approximate data into clean truth." At
v0.1 these existed only as _documentation_ and as heuristic checks in the audit
skill. The boundary-layering enforcement was real but commodity; the
provenance/lineage discipline — the genuinely differentiating idea, proven across
~40 engine modules in the origin project — was not yet operational.

The gap: nothing made laundering _mechanically_ fail. A developer could still
hand-build a clean-looking metadata object from tainted inputs, and only a human
reviewer might catch it.

## Decision

Ship a runtime **provenance primitive** (JS + Python, per
[ADR-0003](0003-two-enforcement-adapters-at-v1.md)) built around one conservative
combination law, exposed through two layers, plus a checker.

**The law** (`combineProvenance`): combining input metadata is conservative —

- `derivedFromMock` = logical OR of every input's taint; **a taint can never be
  cleared by combination**;
- `confidence` = the _weakest_ input on the ordered scale;
- `source` = `derived`;
- `lineage` = the inputs' prior lineage plus one step per input recording that
  input's trust.

Status taxonomy (least→most trustworthy): `unavailable < mock < fallback <
semiReal < derived < real`. Confidence scale: `none < low < medium < high`.

**Two layers, law in one place:**

- the **combinator** layer is the single implementation of the law — and the only
  one;
- the **wrapper** (`mark`/`unwrap`/`derive`) is thin sugar over it. `derive`
  _must_ call `combineProvenance` — it never re-implements the law. A
  shim-equality test asserts the wrapper produces exactly what the combinator
  would, so "two layers" never becomes two sources of truth.

**The checker** (`auditMeta`): a runtime consistency check returning issue
strings (`[]` when clean) — flags laundering, over-claiming, dropped taint, and
unreproducible (`derived` with empty lineage). A team adds one assertion
(`auditMeta(result) === []`) and laundering fails _their own_ test suite.

The decision sentence for users: _new code → use the wrapper (`mark`/`derive`);
existing structures → use the combinators (`combineProvenance`)._

Delivered on the `feature/provenance-primitive` branch (PR #1).

## Consequences

- Laundering becomes structurally hard rather than merely discouraged: honesty is
  enforced by the math, not by a developer remembering.
- The audit skill's checks were sharpened to be primitive-aware (flagging
  hand-built metadata that bypasses the law), connecting static review to the
  runtime checker.
- Dual-language parity is a standing cost — and a real one: final review caught
  two JS/Python divergences in the checker (an empty-meta case and a crash on
  invalid confidence) that had to be fixed to exact parity. Parity is verified by
  a shared case table run in both languages.
- The primitive is deliberately _not_ wired into bootstrap's generated ruleset or
  the principles doc yet — that integration is labelled **planned** to keep this
  decision scoped to the primitive and its checker.
