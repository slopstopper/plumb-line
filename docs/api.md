# plumb-line-provenance — API Reference

This page documents every function and constant exported by the
`plumb-line-provenance` package (JavaScript) and
`plumb_line_provenance` package (Python).
Both packages implement the same specification; see
[`primitives/SPEC.md`](../primitives/SPEC.md) for the language-neutral
normative definition.

---

## Constants

### `STATUS`

Ordered vocabulary of source quality, least-trustworthy first:

```
"unavailable" < "mock" < "fallback" < "semiReal" < "derived" < "real"
```

### `CONFIDENCE`

Ordered vocabulary of confidence level, weakest first:

```
"none" < "low" < "medium" < "high"
```

### `PROVENANCE_VERSION`

Integer schema version of the envelope (currently **schema version 2**). Bump
only on breaking changes to the envelope shape or combination law (see SPEC §1).

---

## Core API

### `mark(value, metaInput?)` / `mark(value, **meta_input)`

Wraps a value with provenance metadata and returns a marked object.

| Parameter | Type | Description |
|---|---|---|
| `value` | any | The value to track |
| `metaInput` / `**meta_input` | object / kwargs | Initial metadata; same options as [`makeMeta`](#makemetaopts--make_meta) |

**Returns** a frozen object (JS) / dict (Python) with the value under the
`value` key and all envelope fields at the top level (JS) or under a `meta`
key (Python).

```js
// JavaScript
const price = mark(99.99, { source: "real", confidence: "high" });
price.source;         // "real"
price.derivedFromMock; // false
```

```python
# Python
price = mark(99.99, source="real", confidence="high")
price["meta"]["source"]           # "real"
price["meta"]["derived_from_mock"] # False
```

---

### `derive(inputs, fn, metaOverride?)` / `derive(inputs, fn, **meta_override)`

Derives a new marked value from one or more marked inputs.

The combination law is applied automatically:

- `derivedFromMock` is the logical OR of all inputs — mock taint **cannot be cleared**.
- `confidence` is the weakest across all inputs.
- `lineage` accumulates all ancestor steps plus one input step per input.

| Parameter | Type | Description |
|---|---|---|
| `inputs` | marked[] | Marked values from `mark` or `derive` |
| `fn` | function | Pure function applied to the unwrapped input values |
| `metaOverride` | object | Optional: override `source`, `confidence`, `confidenceScore`/`confidence_score`, `basis`, or `adapter`. `derivedFromMock`/`derived_from_mock` cannot be cleared. |

**Returns** a marked value with `source: "derived"`.

```js
// JavaScript
const a = mark(10, { source: "real", confidence: "high" });
const b = mark(5,  { source: "mock", confidence: "low" });
const c = derive([a, b], (x, y) => x + y);
c.value;           // 15
c.derivedFromMock; // true  — inherited from b
c.confidence;      // "low" — weakest of the two inputs
```

```python
# Python
a = mark(10, source="real", confidence="high")
b = mark(5,  source="mock", confidence="low")
c = derive([a, b], lambda x, y: x + y)
c["value"]                       # 15
c["meta"]["derived_from_mock"]   # True
c["meta"]["confidence"]          # "low"
```

---

### `metaOf(marked)` / `meta_of(marked)`

Extracts the provenance metadata from a marked value as a plain object / dict.

```js
const m = mark(42, { source: "real", confidence: "high" });
metaOf(m); // { source: "real", confidence: "high", derivedFromMock: false, lineage: [] }
```

---

### `unwrap(marked)`

Extracts the raw value from a marked object, ignoring all metadata.

```js
unwrap(mark(42, { source: "real" })); // 42
```

---

### `auditMeta(meta)` / `audit_meta(meta)`

Checks a provenance envelope for internal consistency.

**Input:** a metadata object / dict (the output of `metaOf`/`meta_of`, or a
manually constructed envelope).

**Returns** `string[]` / `list[str]` — an empty list means the envelope is
consistent. Each string in the list is a human-readable issue prefixed with
a category:

| Prefix | Meaning |
|---|---|
| `"laundering:"` | A clean `source` (`real`, `semiReal`, `fallback`) but `derivedFromMock` is `true` |
| `"over-claiming:"` | `confidence` or `confidenceScore` is higher than the lineage supports |
| `"source over-claim:"` | `weakestSource` is cleaner than the lineage proves |
| `"taint dropped:"` | A tainted lineage step but `derivedFromMock` is `false` |
| `"unreproducible:"` | `source` is `"derived"` but `lineage` is empty |
| `"missing meta"` | Input was `null`/`undefined`/`None` |

```js
auditMeta(metaOf(derive([mark(1, { source: "real", confidence: "high" })], x => x)));
// []
```

---

## Low-level API

These functions implement the combination law and envelope construction.
They are exported for advanced use and testing; most callers should use
`mark` / `derive` / `auditMeta` instead.

### `makeMeta(opts?)` / `make_meta(**kwargs)`

Constructs a provenance metadata envelope (JS: frozen object, Python: dict).

| Field | Default | Description |
|---|---|---|
| `source` | `"derived"` | One of `STATUS` |
| `confidence` | `"none"` | One of `CONFIDENCE` |
| `confidenceScore` / `confidence_score` | — | Numeric `[0, 1]`; omitted if invalid |
| `derivedFromMock` / `derived_from_mock` | `source === "mock"` | Mock-taint flag |
| `lineage` | `[]` | Prior lineage steps; each step is cloned |
| `weakestSource` / `weakest_source` | — | Least-trustworthy source in ancestry |
| `basis` | — | Arbitrary domain metadata |
| `adapter` | — | Adapter identifier |

---

### `combineProvenance(...metas)` / `combine_provenance(*metas)`

Applies the taint-propagation combination law to one or more envelopes and
returns a new derived envelope.

Calling with **zero arguments** returns `source: "unavailable"` (not
`"derived"`), because a value derived from nothing has no honest provenance.

---

### `weakestConfidence(...levels)` / `weakest_confidence(*levels)`

Returns the weakest (lowest-ranked) confidence level. Unknown values are
treated as `"none"`. Returns `"none"` with no arguments.

---

### `weakestSource(...sources)` / `weakest_source(*sources)`

Returns the least-trustworthy source by `STATUS` rank. Unknown values are
ignored. Returns `undefined`/`None` when nothing is rankable.

---

### `combineConfidenceScore(scores)` / `combine_confidence_score(scores)`

Returns the minimum of an array of numeric confidence scores, but **only**
when every element is valid. Returns `undefined`/`None` if any element is
missing — a gap is "unknown", not zero.

---

### `taints(meta)`

Returns `true`/`True` when the envelope carries mock taint
(`derivedFromMock`/`derived_from_mock` is truthy, or `source === "mock"`).

---

### `isScore(x)` / `is_score(x)`

Returns `true`/`True` when `x` is a finite number in `[0, 1]`.
Booleans are excluded in Python.

---

## HTTP adapter

Auto-tags HTTP responses with a provenance envelope by status + cache state
(see ADR-0012). In JavaScript this is the `plumb-line-provenance/http`
subpath; in Python it is the `http` module of the package. The
classification core is dependency-free in both languages; the taggers need a
response object (`fetch`'s native `Response` in JS — Node >= 18 or a browser;
`requests`/`httpx` extras in Python).

The two languages expose different tagger names because they tag different
client libraries; which Python defs are public surface is a 1.0 question
tracked in [#236](https://github.com/slopstopper/plumb-line/issues/236).
This section documents what each module ships today.

### `parseAge(raw)` / `parse_age(raw)`

Parses an RFC 7234 `Age` header value (delta-seconds). Accepts only
OWS-wrapped ASCII digits with an optional fractional part; **returns a
number, or `null`/`None` when the header is not a decimal value** — it never
throws, because header bytes are remote-controlled. Built-in coercions
(`Number()`, `float()`) are deliberately not used: the two languages disagree
on non-decimal strings, which would make cache detection language-dependent.

```js
parseAge("60");    // 60
parseAge(" 60 ");  // 60 (OWS is SP/HTAB only)
parseAge("1e3");   // null — Number("1e3") would be 1000
```

---

### `classifyResponse(status, headers, fromCache?)` / `classify_response(status, headers, from_cache=False)`

Maps an HTTP response to `(source, confidence)`: source is origin trust,
confidence is freshness. A fresh 2xx is `real`/`high`; a cache hit (a 304,
a positive `Age`, an `x-cache` HIT, or an explicit `fromCache`) stays `real`
with confidence dropped to `medium`; anything else is `unavailable`/`none`.
Never emits `fallback` (reserved for caller-supplied substitutes). Returns
`{ source, confidence }` in JS and a `(source, confidence)` tuple in Python.
`headers` may be a `Headers`-like object (`.get`) or a plain object / dict;
lookup is case-insensitive.

The classification behaviour is pinned cross-language by
[`primitives/conformance/http-cases.json`](../primitives/conformance/http-cases.json).

---

### `tagResponse(response, fromCache?)` — JS / `tag_requests(response)`, `tag_httpx(response)` — Python

Tags a client-native response object (`fetch` `Response`; `requests.Response`;
`httpx.Response`) with a provenance envelope via `classifyResponse` /
`classify_response`. The marked value is the response itself — extract with
`derive([tagged], (r) => r.json())`.

```js
import { tagResponse } from "plumb-line-provenance/http";
const m = tagResponse(await fetch(url));
metaOf(m); // { source: "real", confidence: "high", ... }
```

---

### `taggedFetch(url, options?)` — JS / `tagged_get(url, **kwargs)`, `tagged_httpx_get(url, **kwargs)` — Python

Convenience wrappers: perform the request with the client's own function and
tag the response in one call.

---

## Envelope schema

The envelope schema is defined normatively in
[`primitives/SPEC.md`](../primitives/SPEC.md). The fields are:

| camelCase (JS) | snake_case (Python) | Req | Type | Description |
|---|---|---|---|---|
| `source` | `source` | yes | `STATUS` enum | Where the value came from |
| `confidence` | `confidence` | yes | `CONFIDENCE` enum | How certain |
| `derivedFromMock` | `derived_from_mock` | yes | boolean | True if any ancestor was mock-sourced |
| `lineage` | `lineage` | yes | step[] | One step per input at each combine |
| `confidenceScore` | `confidence_score` | no | number `[0,1]` | Finer-grained companion to `confidence` |
| `weakestSource` | `weakest_source` | no | `STATUS` enum | Least-trustworthy source in ancestry |
| `basis` | `basis` | no | any | Free-form provenance note |
| `adapter` | `adapter` | no | any | Enforcement-adapter annotation |

Optional fields are **absent** (not `null`/`undefined`) when they have no
value — absence means "unknown" and is distinct from any present value.

Each lineage **step** records:

| Field | Type | Description |
|---|---|---|
| `id` | string `"step-N"` | Unique within the envelope's lineage |
| `of` | `"input"` | Step kind (currently always `"input"`) |
| `source` | `STATUS` enum | Source of this input |
| `confidence` | `CONFIDENCE` enum | Confidence of this input |
| `derivedFromMock` | boolean | Mock taint of this input |
| `confidenceScore` | number `[0,1]` | Numeric confidence (when present on input) |
