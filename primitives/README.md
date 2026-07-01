# Provenance Primitive

This primitive makes provenance, confidence, and lineage **operational** rather
than advisory. Every value that enters a calculation carries a metadata envelope
(`source`, `confidence`, `derivedFromMock`, `lineage`). The conservative-
combination law means that laundering tainted data is structurally impossible:
once any input is touched by mock or low-confidence data, every value derived
from it inherits that taint automatically — there is no escape hatch, no
override that silently clears the flag. The result is a system where uncertainty
propagates honestly whether or not the developer thinks about it.

The envelope and law are formally specified — see [`SPEC.md`](SPEC.md) (envelope
schema version 1), pinned by the cross-language [conformance suite](conformance/).
Each language is also packaged as `plumb-line-provenance` (npm / PyPI).

---

**New code → use the wrapper (`mark`/`derive`); existing structures → use the combinators (`combineProvenance`).**

---

## The model

Provenance metadata has two independent axes:

| Axis      | Field        | Values (least → most trustworthy)                                     |
| --------- | ------------ | --------------------------------------------------------------------- |
| Status    | `source`     | `unavailable` < `mock` < `fallback` < `semiReal` < `derived` < `real` |
| Certainty | `confidence` | `none` < `low` < `medium` < `high`                                    |

Two additional fields complete the envelope:

- **`derivedFromMock`** (`boolean`) — `true` if this value or any ancestor was
  sourced from mock data. Once set, it cannot be cleared by downstream combination.
- **`lineage`** (`array`) — one step per input captured at each combination point,
  recording that input's `source`, `confidence`, and `derivedFromMock` at the time
  of combination. Enables full audit trails and reproducibility checks.

Two **optional** fields add resolution where the coarse axes lose information:

- **`confidenceScore`** (`number` in `[0,1]`) — a finer-grained companion to the
  four-bucket ordinal `confidence`, travelling *alongside* it (never replacing
  it). Supply it on inputs and it propagates; omit it and nothing changes.
- **`weakestSource`** (`string`) — the least-trustworthy `source` anywhere in the
  value's ancestry, ranked by the `source` ladder above. More resolution than the
  `derivedFromMock` boolean: it distinguishes a value built from `fallback` data
  from one built from `mock`. Computed only — it cannot be hand-set, so it can
  never claim to be cleaner than the lineage proves.

---

## The law

Four rules apply whenever inputs are combined via `combineProvenance` (or the
`derive` wrapper):

1. **`derivedFromMock`** = logical OR over all inputs — mock taint propagates
   forward and cannot be cleared.
2. **`confidence`** = the weakest input confidence — the result is only as
   certain as the least certain thing that fed it.
3. **`source`** = `"derived"` — combined outputs are always labelled as derived,
   never promoted to `"real"`.
4. **`lineage`** = all inputs' prior lineage steps, followed by one new step per
   input capturing its trust state at this combination point.

Two optional fields extend the law, both **conservatively**:

5. **`confidenceScore`** = the **minimum** across inputs — but only when *every*
   input carries one. A missing score means "unknown", and an unknown cannot be
   dropped from a minimum, so any gap omits the field rather than over-claiming.
   This is the higher-resolution analog of rule 2, not error-propagation:
   narrowing uncertainty through combination would require an independence
   assumption a domain-neutral library must not bake in, so the law stays at
   `min`.
6. **`weakestSource`** = the weakest `source` across the whole resulting lineage,
   ranked by the `source` ladder.

---

## JavaScript example

```js
import { mark, derive, metaOf, auditMeta } from "./primitives/js/index.mjs";

// A real base amount with high confidence.
const baseAmount = mark(1000, { source: "real", confidence: "high" });

// A mock exchange rate with low confidence.
const exchangeRate = mark(1.25, { source: "mock", confidence: "low" });

// Derive a total — the law fires automatically.
const total = derive([baseAmount, exchangeRate], (a, r) => a * r);

console.log(total.value); // 1250
console.log(total.derivedFromMock); // true  — inherited from exchangeRate
console.log(total.confidence); // 'low' — weakest of 'high' and 'low'
console.log(total.source); // 'derived'

// You cannot get a clean value out of a tainted one.
// Any further derive() using `total` will also carry derivedFromMock: true.
const rounded = derive([total], (v) => Math.round(v));
console.log(rounded.derivedFromMock); // true
```

The JS wrapper uses a **spread shape**: `mark` returns `{ value, source,
confidence, derivedFromMock, lineage, ... }` — meta fields sit alongside
`value` in a single flat object. `metaOf(marked)` extracts just the meta
fields when you need to pass them to `combineProvenance` directly.

---

## Python example

```python
from provenance import combine_provenance
from marked import mark, derive, meta_of

# A real base amount with high confidence.
base_amount = mark(1000, source='real', confidence='high')

# A mock exchange rate with low confidence.
exchange_rate = mark(1.25, source='mock', confidence='low')

# Derive a total — the law fires automatically.
total = derive([base_amount, exchange_rate], lambda a, r: a * r)

print(total['value'])                    # 1250.0
print(total['meta']['derived_from_mock'])  # True  — inherited from exchange_rate
print(total['meta']['confidence'])         # 'low' — weakest of 'high' and 'low'
print(total['meta']['source'])             # 'derived'

# You cannot get a clean value out of a tainted one.
rounded = derive([total], lambda v: round(v))
print(rounded['meta']['derived_from_mock'])  # True
```

The Python wrapper uses a **nested shape**: `mark` returns
`{'value': ..., 'meta': {...}}`. Meta fields use `snake_case`
(`derived_from_mock`). `meta_of(marked)` returns the inner `meta` dict.

---

## The checker

`auditMeta(meta)` (JS) / `audit_meta(meta)` (Python) validates a metadata
envelope and returns a list of issue strings. An empty list means the envelope
is internally consistent.

It catches six categories of problem:

- **Laundering** — a clean `source` (`real`, `semiReal`, `fallback`) with
  `derivedFromMock: true`.
- **Over-claiming** — `confidence` higher than the weakest confidence in the
  lineage.
- **Numeric over-claiming** — `confidenceScore` higher than the weakest
  `confidenceScore` in the lineage (the resolution-bearing analog of the above).
- **Source over-claim** — `weakestSource` cleaner than the weakest `source`
  actually present in the lineage.
- **Dropped taint** — lineage contains a tainted step but `derivedFromMock` is
  `false`.
- **Unreproducible** — `source` is `"derived"` but `lineage` is empty.

**Adding a consistency assertion (JS):**

```js
import { auditMeta, metaOf } from "./primitives/js/index.mjs";

// After any mark/derive call:
const issues = auditMeta(metaOf(total));
console.assert(issues.length === 0, "provenance inconsistency", issues);
```

**Adding a consistency assertion (Python):**

```python
from audit import audit_meta
from marked import meta_of

issues = audit_meta(meta_of(total))
assert issues == [], f"provenance inconsistency: {issues}"
```

### Structural validation — the complement

`auditMeta` checks the *logic* among the fields that are present, and treats an
absent field as "unknown" (SPEC §2). That is deliberate, but it means a
structurally empty envelope `{}` passes the audit — there are no claims to
contradict. `validateEnvelope(meta)` (JS) / `validate_envelope(meta)` (Python) is
the structural complement: it checks that the four **required** fields (`source`,
`confidence`, `derivedFromMock`, `lineage`) are present and well-typed, returning
the same list-of-issue-strings shape (empty = structurally valid). Like the
audit, it is total — `null`/`None` and non-objects yield a list, never an
exception. Run `validateEnvelope` at trust boundaries (deserialized input,
cross-service envelopes); run `auditMeta` to check the claims once the shape is
known good.

```js
import { validateEnvelope } from "./primitives/js/index.mjs";

const structural = validateEnvelope(incoming); // [] if all required fields present
if (structural.length) throw new Error(`malformed envelope: ${structural}`);
```

---

## Status

| Artefact                                                | Status  |
| ------------------------------------------------------- | ------- |
| JS primitives (`primitives/js/`)                        | current |
| Python primitives (`primitives/python/`)                | current |
| Optional numeric confidence + weakest-source resolution | current |
| Cross-language conformance suite (`conformance/`)       | current |
| AST-level static lint rule (`adapters/*/provenance-lint`) | current |
| `validateEnvelope` structural field-presence checker    | current |
| Per-output `PROVENANCE_VERSION` embedding in envelopes  | planned |
| Bootstrap / ruleset wiring for host projects            | planned |
