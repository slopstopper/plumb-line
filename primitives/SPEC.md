# plumb-line Provenance Envelope — Specification

**Status:** current · **Envelope schema version:** 1 · **SPEC revision:** 1.2

This is the normative, language-neutral definition of the provenance envelope,
the conservative-combination law, and the consistency checks. Any implementation
that conforms to this document interoperates with any other, regardless of
language. The reference implementations (`primitives/js/`, `primitives/python/`)
conform; the executable definition of conformance is
[`conformance/cases.json`](conformance/cases.json), exercised in both languages
(`js/conformance.test.mjs`, `python/test_conformance.py`).

The key words MUST, MUST NOT, SHOULD, MAY are used as in RFC 2119.

---

## 1. The envelope

A **provenance envelope** is a record describing the trust state of a value. It
has four required fields and several optional ones.

| Field             | Req | Type            | Meaning                                                              |
| ----------------- | --- | --------------- | ------------------------------------------------------------------- |
| `source`          | yes | enum (§2)       | Where the value came from, on the status ladder.                    |
| `confidence`      | yes | enum (§2)       | How certain, on the four-level ordinal ladder.                      |
| `derivedFromMock` | yes | boolean         | `true` if this value or any ancestor was mock-sourced.              |
| `lineage`         | yes | array of step   | One step per input captured at each combination (§4).               |
| `confidenceScore` | no  | number `[0,1]`  | Higher-resolution companion to `confidence` (§3).                   |
| `weakestSource`   | no  | enum (§2)       | Least-trustworthy `source` in the ancestry; computed only (§4).     |
| `basis`           | no  | any             | Free-form note on what the value is based on.                       |
| `adapter`         | no  | any             | Free-form enforcement-adapter annotation.                           |

Field names are given here in `camelCase` (the canonical/JSON form). A
`snake_case` binding (`derived_from_mock`, `confidence_score`, `weakest_source`)
is permitted and is what the Python implementation uses; the two are the same
envelope under a naming convention, and `conformance/cases.json` is authored in
`camelCase` with bindings translating as needed.

Optional fields MUST be **absent** when they have no value — an implementation
MUST NOT emit `confidenceScore: null` or `weakestSource: undefined`. Absence is
meaningful: it denotes "unknown", which is distinct from any present value.

### Envelope versioning

The envelope schema carries a version constant (`PROVENANCE_VERSION`, currently
`1`). Adding a new **optional** field is backward-compatible and MUST NOT bump
the version (`confidenceScore` and `weakestSource` were added under v1). Removing
or renaming a field, changing a field's type, or changing the combination law's
result for an existing case is a breaking change and MUST bump the version —
**except** when the prior result violated another normative section of this SPEC
(e.g. an output that §5 flags as inconsistent). Correcting a self-contradiction
to a result no conformant consumer could have relied on is a conformance fix,
not a breaking change, and MUST NOT bump the version; such fixes MUST be recorded
(CHANGELOG + an ADR) and pinned by a conformance case. The zero-input combine
correction (§3, `source` `"derived"` → `"unavailable"`) is the first such fix.

---

## 2. Ordered vocabularies

Two fields draw from ordered enumerations. Order is significant: "weakest" and
"cleaner/dirtier" comparisons are defined by position.

**`source`** — status ladder, least → most trustworthy:

```
unavailable  <  mock  <  fallback  <  semiReal  <  derived  <  real
```

**`confidence`** — certainty ladder, least → most certain:

```
none  <  low  <  medium  <  high
```

A value not present in a ladder is **unknown**. For `confidence`, an unknown
input MUST be treated as the weakest (`none`) by the combination law (§3) and
MUST be ignored by the audit's over-claim comparison (§5). For `source`, unknown
values are ignored when computing `weakestSource` (§4).

---

## 3. The combination law

When N input envelopes are combined into one output envelope, the output MUST be
computed as follows. The law is **conservative**: the result is never more
trustworthy than its inputs, and taint can never be cleared.

1. **`derivedFromMock`** = logical OR over all inputs. An input taints if its
   `derivedFromMock` is `true` OR its `source` is `mock`. Once `true`, no
   downstream combination may set it back to `false`.
2. **`confidence`** = the weakest (lowest-ranked) `confidence` among the inputs.
3. **`confidenceScore`** = the minimum across inputs **iff every input carries a
   valid score**; otherwise the field is omitted. A missing score is "unknown"
   and MUST NOT be dropped from the minimum — any gap omits the result.
   - This is the higher-resolution analog of rule 2, **not** error propagation.
     Narrowing uncertainty through combination requires an independence
     assumption a domain-neutral law MUST NOT bake in. The law stays at `min`.
4. **`source`** = the literal `"derived"`. Combined outputs MUST NOT be promoted
   to `real` (or any clean status) by the law itself.
5. **`lineage`** = every input's prior lineage steps, concatenated, followed by
   one new step per input (§4).
6. **`weakestSource`** = the weakest `source` across the entire resulting
   `lineage` (§4). Omitted when the lineage is empty.

The law MUST be **order-independent** for fields 1–4 and 6: permuting the inputs
MUST NOT change the result except for the order of lineage steps.

### Combining zero inputs

A value combined from no inputs is derived from nothing, so it MUST NOT claim
`source = "derived"` — that would be a derived value with an empty `lineage`,
which §5 (condition 6) flags as unreproducible. Combining zero inputs MUST
instead yield `source = "unavailable"`, `confidence = "none"`,
`derivedFromMock = false`, `lineage = []`, with `confidenceScore` and
`weakestSource` absent. This envelope MUST audit clean.

---

## 4. Lineage steps

A **lineage step** records one input's trust state at the moment of combination.
Each new step MUST contain:

| Field             | Type    | Meaning                                          |
| ----------------- | ------- | ------------------------------------------------ |
| `id`              | string  | Unique-within-output identifier.                 |
| `of`              | string  | `"input"` for steps minted by the law.           |
| `source`          | enum    | The input's `source` at combination time.        |
| `confidence`      | enum    | The input's `confidence` at combination time.    |
| `derivedFromMock` | boolean | Whether the input tainted (flag OR mock source). |
| `confidenceScore` | number  | Present **iff** the input carried a valid score. |

`weakestSource` is **computed only**: it is derived from the lineage and MUST NOT
be settable as a combination override. An implementation MUST NOT let a caller
hand-set `weakestSource` to a value cleaner than the lineage proves (the audit in
§5 catches violations).

An output whose `source` is `"derived"` MUST have a non-empty `lineage`; a
derived value with no lineage is unreproducible (§5).

---

## 5. Consistency checks (the audit)

An implementation MUST provide a checker (`auditMeta` / `audit_meta`) that takes
one envelope and returns a list of issue strings — empty meaning consistent. The
checker MUST detect each of the following:

| # | Issue                  | Condition                                                                                  |
| - | ---------------------- | ------------------------------------------------------------------------------------------ |
| 1 | Laundering             | a clean `source` (`real`, `semiReal`, `fallback`) with `derivedFromMock: true`.            |
| 2 | Over-claiming          | `confidence` ranked higher than the weakest `confidence` in the lineage.                   |
| 3 | Numeric over-claiming  | `confidenceScore` greater than the weakest `confidenceScore` in the lineage.               |
| 4 | Source over-claim      | `weakestSource` cleaner (higher-ranked) than the weakest `source` present in the lineage.  |
| 5 | Dropped taint          | a tainted lineage step exists but `derivedFromMock` is `false`.                            |
| 6 | Unreproducible         | `source` is `"derived"` but `lineage` is empty.                                            |

The checker MUST be total: a missing or malformed field MUST yield a result list
(possibly noting the problem), never an exception. A `null`/`None` envelope MUST
return a single "missing meta" issue. An empty envelope `{}` MUST return `[]`.

### 5a. Structural validation

The audit above checks the *logic* of the claims an envelope makes and treats an
absent field as "unknown" (§2) — so a structurally empty `{}` audits clean
(`[]`), because it asserts nothing to contradict. The audit therefore does **not**
verify that the four required fields (§1) are present.

An implementation MUST also provide a structural validator
(`validateEnvelope` / `validate_envelope`) that takes one envelope and returns a
list of issue strings — empty meaning structurally valid. It MUST detect:

- each of the four required fields (`source`, `confidence`, `derivedFromMock`,
  `lineage`) that is **absent**; and
- each required field that is **present but of the wrong type** (`source` and
  `confidence` MUST be strings, `derivedFromMock` a boolean, `lineage` an array).

Like the audit, the validator MUST be total: a `null`/`None` envelope MUST return
a single `"missing meta"` issue, and a non-object (string, number, array) MUST
return a single `"not an envelope object"` issue, never an exception. The
validator MUST NOT check enum membership of `source`/`confidence` (that is the
audit's tolerant-of-unknown domain, §2) — its sole concern is required-field
presence and type. The two checkers are complementary and independent: an
envelope MAY pass one and fail the other.

---

## 6. Static enforcement (review-time)

The audit (§5) checks an envelope that already exists, at run time. A **static
lint** catches the source-code patterns that *produce* inconsistent envelopes —
bypassing the combination law (§3) or laundering taint by hand — before the code
runs. It is keyed to the primitive's own functions (`mark`, `derive`,
`makeMeta`/`make_meta`, `unwrap`) and is the review-time complement to the audit.

A conforming static lint SHOULD flag the following four patterns. Each fires only
at a **resolved primitive call site** (the function is import-bound to the
primitive) and only on **literal** field values — a dynamic value cannot be
proven a violation and MUST NOT be flagged (under-claim over false positives).
The fields are an object literal in JS (`mark(v, {…})`) and keyword arguments in
Python (`mark(v, source=…)`); the rules are otherwise identical.

| ID  | Pattern                                                                                              | Run-time analog (§5) |
| --- | ---------------------------------------------------------------------------------------------------- | -------------------- |
| PB1 | a clean `source` (`real`/`semiReal`/`fallback`) asserted together with `derivedFromMock` literal `true` | laundering (#1) |
| PB2 | `derivedFromMock` literal `false` passed as a `derive` **override** (a genuine no-op the law ignores) | — |
| PB3 | a clean `source` passed as a `derive` override (relabeling a derived value)                           | laundering (#1) |
| PB4 | `mark(unwrap(x), …)` — re-marking a value pulled out via the import-bound `unwrap`, dropping its lineage | unreproducible (#6) |

Reference implementations: `adapters/js/provenance-lint/` (an ESLint rule,
`no-provenance-bypass`) and `adapters/python/provenance_lint.py` (a stdlib-`ast`
checker). Both flag PB1–PB4 and stay silent on honest usage and on dynamic
values. The catalogue is intentionally **zero-false-positive**: each rule keys on
an unambiguous form, so cases needing dataflow to judge are deliberately left
out — PB2 fires only on a `derive` override (a literal `derivedFromMock:false` on
a plain `mark`/`makeMeta` is the honest stored default, not a violation), and PB4
fires only on the import-bound `unwrap(x)` (a bare `x.value` could be any raw
field). Whole-program dataflow is out of scope for envelope schema version 1.

---

## 7. Conformance

An implementation **conforms to envelope schema version 1** if, for every case in
`conformance/cases.json`:

- each `combine` case's output matches the expected fields and respects the
  declared `absent` fields,
- each `audit` case's issue list contains the expected substrings (or is empty
  when none are expected), and
- each `validate` case's issue list contains the expected substrings (or is empty
  when none are expected).

Conformance is verifiable mechanically — see [`conformance/`](conformance/) and
the report tool documented there. New behavior MUST be added to `cases.json`
(covering all languages at once) before or alongside the implementation change.

---

## 8. Reference

- Model, law, worked examples (prose): [`primitives/README.md`](README.md)
- Cross-language parity table: [`primitives/PARITY.md`](PARITY.md)
- The discipline this primitive operationalizes (Principles 3, 4, 8):
  [`reference/portable-principles.md`](../reference/portable-principles.md)
