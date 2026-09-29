# plumb-line-provenance — API Reference

This page documents the user-facing API of the `plumb-line-provenance`
package (JavaScript) and the `plumb_line_provenance` package (Python): every
name exported from the JS main entry (except the test-only
`__resetStepCounter`) and the Python package's `__all__`, the
HTTP adapter (JS `/http` subpath, Python `http_adapter`), the golden-baseline
API, and the Python dataframe/array wrappers. `scripts/test_api_reference.py`
fails when one of those gains a name this page has no heading for. The JS
`/baseline` subpath also exports internal helpers (`canonicalJson`,
`deepEqual`, and others) used by its own tests; they are not documented here
and are not a stable API (the 1.0 surface is decided in
[#236](https://github.com/slopstopper/plumb-line/issues/236)).
Both packages implement the same specification; see
[`primitives/SPEC.md`](../primitives/SPEC.md) for the language-neutral
normative definition.

---

## Constants

### `STATUS`

Ordered vocabulary of source quality, least-trustworthy first:

`unavailable` < `mock` < `inferred` < `fallback` < `semiReal` < `derived` < `real`

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

### `mark(value, metaInput)` / `mark(value, **meta_input)`

Wraps a value with provenance metadata and returns a marked object.

| Parameter | Type | Description |
|---|---|---|
| `value` | any | The value to track |
| `metaInput` / `**meta_input` | object / kwargs | Initial metadata; same options as [`makeMeta`](#makemetaopts--make_metakwargs), so `source` is required |

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
metaOf(m); // { provenanceVersion: 2, source: "real", confidence: "high", derivedFromMock: false, lineage: [] }
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
| `"taint dropped:"` | A lineage step that taints (by the rule of `taints`) but `derivedFromMock` is `false` |
| `"unreproducible:"` | `source` is `"derived"` but `lineage` is empty |
| `"version-legacy:"` | `provenanceVersion` is absent or lower than the current wire version (advisory; `{}` returns only this) |
| `"version-future:"` | `provenanceVersion` is newer than this library supports |
| `"version-malformed:"` | `provenanceVersion` is present but not a finite number, or has a fractional part |
| `"non-plain meta:"` | The container is the wrong type but could carry an envelope: a `dict` subclass in Python (`OrderedDict`, `defaultdict`), a null-prototype object in JS. Rebuild with `dict(meta)` / `{...meta}` |
| `"missing meta"` | `null`/`undefined`/`None`, a primitive, an array/list, or any other non-plain object (`Map`, `Date`, class instances) |

The version and non-plain prefixes are defined in SPEC §5 and §5b.

```js
auditMeta(metaOf(derive([mark(1, { source: "real", confidence: "high" })], x => x)));
// []
```

---

### `validateEnvelope(meta)` / `validate_envelope(meta)`

The *structural* checker, complementary to `auditMeta`: it verifies the four
required fields (`source`, `confidence`, `derivedFromMock`, `lineage`) are
present and well-typed (SPEC §5a). `auditMeta` checks logical consistency and
tolerates absence as "unknown"; `validateEnvelope` does not. Total: returns a
list of issue strings (`missing required field: …`, `field '…' must be …`,
`missing meta`, `not an envelope object`) and never throws.

```js
validateEnvelope({ source: "real" });
// ["missing required field: confidence", "missing required field: derivedFromMock", "missing required field: lineage"]
```

---

### `guard(x, options?)` / `guard(x, *, no_mock=True, min_confidence='none')`

The egress guard (since v0.12.0, #120; ADR-0020). `auditMeta` reports a
problem after the fact; `guard` stops a value at an output point (an export,
a display, a publish) unless its envelope backs what the output claims
(SPEC §5c). On success it returns the value it was given, unchanged, so the
output point writes `unwrap(guard(x))`. Otherwise it throws
[`ProvenanceRefused`](#provenancerefused) listing every reason.

| Option | Default | Refuses when |
|---|---|---|
| `noMock` / `no_mock` | `true` / `True` | mock taint appears anywhere: `derivedFromMock`, `source`, `weakestSource` or any lineage step. On unless turned off (Principle 4's mock clause: excluded from outputs unless explicitly opted in. Fallback data, cached data (which the HTTP adapter marks `real`) and approximate data (no rung of its own) are not refused, nor are `inferred`, `semiReal` or `unavailable` sources; #541) |
| `minConfidence` / `min_confidence` | `"none"` | the weakest confidence in the envelope *or its lineage* is below this level (a lineage step with no confidence counts as `none`) |

It fails closed, whatever the options:
- a value that is not marked (`42`, `null`, a list, a `Map`) is refused;
- so is a malformed envelope: any `validateEnvelope` issue, a `source`,
  `confidence` or `weakestSource` off its ladder, a lineage step that is not
  a plain object (a Python dict), a step with no `source` (#525), a step
  whose `source` or `confidence` is off its ladder or whose
  `derivedFromMock` is not a boolean, or a
  `confidenceScore`, top-level or on a step, that is not a number in `[0, 1]`;
- and so is one the audit flags: any `auditMeta` issue except the
  `version-legacy:` and `version-future:` advisories. An envelope from an older
  or newer library is judged on what it carries (SPEC §5b).

A bad option is a programmer error, a `TypeError` in both languages, raised
before the value is looked at and never a `ProvenanceRefused`: options that
are not a plain object (JS), an unknown option, a non-boolean `noMock`, or a
`minConfidence` off the ladder. Its message starts `guard: `. Because a
refusal is a `ValueError` in Python and a bad option never is, catching one
cannot swallow the other. In Python, `min_confidence=None` is an error rather
than the default, as `make_meta` refuses `None`.

```js
// JavaScript
const total = derive([mark(100, { source: "real", confidence: "high" }),
                      mark(1.17, { source: "mock", confidence: "low" })], (a, r) => a * r);
guard(total);                                  // throws ProvenanceRefused: mock: …
unwrap(guard(total, { noMock: false }));       // 117 — mock explicitly allowed
guard(total, { noMock: false, minConfidence: "medium" });
// throws: confidence: low is below the required medium
```

```python
# Python
total = derive([mark(100, source="real", confidence="high"),
                mark(1.17, source="mock", confidence="low")], lambda a, r: a * r)
guard(total)                                   # raises ProvenanceRefused: mock: …
unwrap(guard(total, no_mock=False))            # 117.0 — mock explicitly allowed
```

The refusals are pinned for both languages by the `guard` kind in
[`primitives/conformance/cases.json`](../primitives/conformance/cases.json).

---

### `ProvenanceRefused`

What `guard` throws (JS: an `Error` subclass) or raises (Python: a
`ValueError` subclass) when a value may not leave. `reasons` lists every
reason, each prefixed with its class — `not a marked value`,
`invalid envelope:`, `audit:`, `mock:`, `confidence:` — and the message is
`provenance refused: ` followed by the reasons joined with `; `, the same in
both languages. A display that should show "unavailable" instead of failing
catches it:

```js
let shown;
try { shown = unwrap(guard(price, { minConfidence: "medium" })); }
catch (e) { if (e instanceof ProvenanceRefused) shown = "unavailable"; else throw e; }
```

---

## Low-level API

These functions implement the combination law and envelope construction.
They are exported for advanced use and testing; most callers should use
`mark` / `derive` / `auditMeta` instead.

### `makeMeta(opts)` / `make_meta(**kwargs)`

Constructs a provenance metadata envelope (JS: frozen object, Python: dict).

| Field | Default | Description |
|---|---|---|
| `source` | none: required | One of `STATUS`; anything else, or leaving it out, is refused |
| `confidence` | `"none"` | One of `CONFIDENCE`; anything else, including a number, is refused |
| `confidenceScore` / `confidence_score` | — | Numeric `[0, 1]`; omitted if invalid |
| `derivedFromMock` / `derived_from_mock` | `source === "mock"` | Mock-taint flag |
| `lineage` | `[]` | Prior lineage steps; each step is cloned |
| `weakestSource` / `weakest_source` | — | Least-trustworthy source in ancestry |
| `basis` | — | Arbitrary domain metadata |
| `adapter` | — | Adapter identifier |

Every envelope `makeMeta` builds is stamped with `provenanceVersion` (the
current `PROVENANCE_VERSION`); callers do not pass it.

A `source` outside `STATUS` or a `confidence` outside `CONFIDENCE` is refused
(since v0.12.0, #443). JS throws an `Error` and Python raises `ValueError`.
Both messages start the same way,
`confidence must be one of none, low, medium, high; got 0` (or the `source`
equivalent), though the quoted value can differ in form between the two. In
Python, `None` is refused rather than defaulted, matching JS `null`. This
applies to `mark` and to a `derive` override, which build on `makeMeta`. A
numeric certainty belongs in `confidenceScore`.

`source` has no default (since v0.12.0, #177). Leaving it out throws or raises
`source is required (one of unavailable, mock, inferred, fallback, semiReal,
derived, real)`, the same message in both languages. The old default,
`"derived"`, was untrue of a leaf, which has no parents, and such an envelope
audited as `unreproducible`. `confidence` still defaults to `"none"`. `derive`
is not a leaf: its `source` comes from the combination law, and in JS an
override of `source: undefined` counts as no override. Envelopes you are
*handed*, such as parsed JSON, are not refused: `combineProvenance` and the
audit still tolerate unknown values in them (SPEC §2).

---

### `combineProvenance(...metas)` / `combine_provenance(*metas)`

Applies the taint-propagation combination law to one or more envelopes and
returns a new derived envelope.

Calling with **zero arguments** returns `source: "unavailable"` (not
`"derived"`), because a value derived from nothing has no honest provenance.

It accepts any input (SPEC §3, #525). An input that is not an envelope, or an
envelope with no `source` or `confidence`, gives a step with that field
`null`; the egress guard refuses a step with a `null` or missing `source`. A
lineage that is not an array contributes no prior steps, and prior steps are
kept as they are.

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

Returns `true`/`True` when the envelope carries mock taint:
`derivedFromMock`/`derived_from_mock` is anything other than `false` or
absent (`null`/`None` counts as absent), or `source === "mock"`. Not
truthiness: a handed `0`, `""`, `[]` or `{}` taints, in both languages
(SPEC §3, #525). A value that is not an envelope carries no taint.

---

### `isScore(x)` / `is_score(x)`

Returns `true`/`True` when `x` is a finite number in `[0, 1]`.
Booleans are excluded in Python.

---

### `stepId(step, inputIds?)` — JS

The content-addressed id of a lineage step: `"sha256:"` plus the first 12
hex characters of a SHA-256 over the step's canonical form (SPEC §4, which
gives the form and two worked examples). Stable across recombination and
identical in both languages. `combineProvenance` calls it; it is exported for
ports and tests. (Python has the same function as `step_id` in its
`provenance` module, not re-exported from the package.)

---

## HTTP adapter

Auto-tags HTTP responses with a provenance envelope by status + cache state
(see ADR-0012). In JavaScript this is the `plumb-line-provenance/http`
subpath; in Python it is the `http_adapter` module of the package
(`plumb_line_provenance.http` still works as an alias through 0.x, #429). The
classification core is dependency-free in both languages; the taggers need a
response object (`fetch`'s native `Response` in JS — Node >= 22, the
package's floor, or a browser; `requests`/`httpx` extras in Python).

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
A rejected value is not merely ignored downstream: `classifyResponse` treats
a present-but-unreadable `Age` as grounds to degrade freshness to `medium`
(ADR-0014).

```js
parseAge("60");    // 60
parseAge(" 60 ");  // 60 (OWS is SP/HTAB only)
parseAge("1e3");   // null — Number("1e3") would be 1000
```

---

### `classifyResponse(status, headers, fromCache?)` / `classify_response(status, headers, from_cache=False)`

Maps an HTTP response to `(source, confidence)`: source is origin trust,
confidence is freshness. A 304 is `real`/`medium`. A 2xx is `real`/`high`
when fresh, dropping to `real`/`medium` when a cache signal is present (a
positive `Age`, an `x-cache` HIT, or an explicit `fromCache`) — or when an
`Age` header is present but unreadable: a staleness signal we can see but
cannot parse degrades the freshness claim rather than counting as absent
(ADR-0014). Any other
status is `unavailable`/`none` — cache signals are not consulted outside
the 2xx and 304 paths, so a 404 with `Age: 60` is still `unavailable`.
Never emits `fallback` (reserved for caller-supplied substitutes). Returns
`{ source, confidence }` in JS and a `(source, confidence)` tuple in Python.
`headers` may be a plain object / dict, which is scanned case-insensitively,
or a `.get()`-bearing object, which is queried as `.get("age")` /
`.get("x-cache")` — casing is then the object's responsibility (`fetch`'s
`Headers`, `requests`' `CaseInsensitiveDict` and `httpx.Headers` all
normalize; a bare `Map` does not).

The classification behaviour is pinned cross-language by
[`primitives/conformance/http-cases.json`](../primitives/conformance/http-cases.json).

---

### `tagResponse(response, fromCache?)` — JS / `tag_requests(response)`, `tag_httpx(response)` — Python

Tags a client-native response object (`fetch` `Response`; `requests.Response`;
`httpx.Response`) with a provenance envelope via `classifyResponse` /
`classify_response`. The marked value is the response itself. In Python
extract with `derive([tagged], lambda r: r.json())`. In JS the body is read
asynchronously and `derive` is synchronous, so read first, then derive:
`const json = await unwrap(tagged).json(); derive([tagged], () => json)`
(`derive([tagged], (r) => r.json())` would mark a Promise).

Cache state is signaled differently per language: JS takes an explicit
`fromCache` argument, while the Python taggers have no cache parameter and
instead read a `from_cache` attribute off the response when one is present
(`bool(getattr(response, "from_cache", False))` — the convention
`requests-cache` uses). The taggers accept only a real `requests.Response` /
`httpx.Response` and raise `TypeError` for anything else, so the attribute is
read only on those. Stock clients never set it, so for them cache detection
comes from the status and headers alone. A `Response` subclass that sets a
truthy `from_cache` for another reason will read as a cache hit.

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

## Test fixtures (#123)

The fixture quarantine: fake data belongs in tests, and these helpers make
the quarantine explicit there (ADR-0021). Marking is opt-in per fixture. The
no-taint check is `guard` (above) with its defaults, so it fails on mock taint anywhere in the lineage, and on
an unmarked or malformed value too; it takes a marked value only (walking a
structure is assessed in #544). Both languages fail with the same message
prefix: `no mock taint may reach a golden output: provenance refused: …`.
Neither helper is in the plugin's bundled copy: they are test tooling, and the
bundle is the dependency-free runtime.

### `plumb_mock_fixture` — Python (pytest)

`pytest.fixture`, with the fixture's value marked `source='mock'`. Use it as
`@plumb_mock_fixture` or `@plumb_mock_fixture(scope=...)`: keyword arguments
go to `pytest.fixture`. A generator fixture's yielded value is marked and its
teardown still runs; one that never yields reports it as pytest does. A
fixture that returns an already-marked value raises `TypeError` (marking it
again would nest it, or hide a `real` label behind `mock`). "Already marked"
means its envelope is structurally valid (SPEC §5a), whatever its source, so
ordinary data with `value` and `meta` keys is marked like any other. An async fixture is refused at decoration. Import it from
`plumb_line_provenance.pytest_plugin`. The package registers that module as a
pytest plugin through its `pytest11` entry point, under the module's own name,
so naming it in `pytest_plugins` or `-p` as well is harmless. It adds no hooks,
fixtures or options, and it is the only module in the package that imports
pytest. Loading it does import the package at every pytest start in that
environment; turn it off with `-p no:plumb_line_provenance.pytest_plugin`.

### `assert_no_taint(output)` — Python / `assertNoTaint(output)` — JS

Fails the test unless `guard(output)` passes: Python raises `AssertionError`
(never a `ValueError`, with no chained cause and the plugin's frame hidden, so
the report is the reasons at the test); JS throws an `Error`. Returns nothing.

### `assert_tainted(output)` — Python / `assertTainted(output)` — JS

The positive claim, verified: fails unless `guard` refuses `output` **for mock
taint**. A value `guard` lets through fails (`… guard let it through`), and so
does one it refuses for another reason, an unmarked or malformed value, which
is not proof that taint reached it (`… guard refused it, but not for mock
taint: …`). Both languages fail with the prefix `mock taint was expected to
reach this value:`.

### `markFixture(value)` — JS (`plumb-line-provenance/vitest`)

Marks a fixture's value `source: "mock"` and returns it. An already-marked
value (a plain object whose envelope fields form a valid envelope) throws
`TypeError`, as in Python; ordinary data with a `value` key is marked like any
other.

### `plumbMatchers` — JS (`plumb-line-provenance/vitest`)

Matchers for `expect.extend(plumbMatchers)`: `expect(x).toBeUntainted()` is
`assertNoTaint` as a matcher, and `.not.toBeUntainted()` is `assertTainted`:
it passes only when `guard` refuses the value for mock taint, not for a value
refused for any other reason. The subpath never imports vitest, so the package stays
dependency-free; the caller registers the matchers.

```js
import { expect } from "vitest";
import { mark, derive } from "plumb-line-provenance";
import { markFixture, plumbMatchers } from "plumb-line-provenance/vitest";
expect.extend(plumbMatchers);

const amount = mark(100, { source: "real", confidence: "high" });
const price = derive([amount, markFixture(1.17)], (a, r) => a * r);
expect(price).not.toBeUntainted();   // the fixture's taint reached it
expect(amount).toBeUntainted();
```

```python
from plumb_line_provenance import mark, derive
from plumb_line_provenance.pytest_plugin import plumb_mock_fixture, assert_no_taint

@plumb_mock_fixture
def rate():
    return 1.17

def test_price(rate):
    amount = mark(100, source='real', confidence='high')
    assert_no_taint(derive([amount, rate], lambda a, r: a * r))  # fails: mock reached it
```

---

## Golden baseline

Pins a derived value *with its envelope* as a golden record and refuses silent
drift (Principle 9; ADR-0015). JS: the `plumb-line-provenance/baseline`
subpath (it touches `node:fs`, so the main entry does not re-export it).
Python: exported from the package. Records live in `.plumb-line/baselines/`
unless `dir` is passed. A read-only CLI inspects them:
`node node_modules/plumb-line-provenance/baseline-cli.mjs` /
`python -m plumb_line_provenance.baseline` (`list`, `show <name>`,
`validate`, with `--dir`).

### `update(name, marked, { because, dir, date })` / `update(name, marked, because=, dir=, date=)`

Records `marked`'s value and envelope as the baseline `name`, appending
`{ date, because, change }` to the record's append-only history. `because` is
required and must be non-empty: accepting a new state needs a reason.

### `check(name, marked, { dir })` / `check(name, marked, dir=)`

Compares `marked` with the stored baseline and returns a report:
`status` (`match`, `drift`, `missing`, `invalid` or `invalid-envelope`), the
attributed `findings`, a one-line `summary`, and any `issues`. Never throws on
drift.

### `assertBaseline(name, marked, { dir })` / `assert_baseline(name, marked, dir=)`

`check`, but throws (JS `Error`, Python `AssertionError`) with the attributed
findings unless the status is `match`.

### `list({ dir })` — JS / `list_baselines(dir=)` — Python

The names of the recorded baselines. (Python avoids shadowing the `list`
builtin.)

### `show(name, { dir })` / `show(name, dir=)`

The stored record for `name`. Throws when there is no such record or it is not a valid baseline record.

### `validateBaseline(record)` / `validate_baseline(record)`

The record-format validator: returns a list of issues, empty when the record
conforms to `baseline-format: v1`. Never throws.

Compared on `check`: each lineage step's trust fields and `of`, the lineage
length, the top-level trust fields and `basis`, then the value. Cross-step
causality, structural diffing inside a nested value and float tolerance are
`not-implemented`.

---

## Dataframe and array wrappers (Python)

Optional extras (`pip install "plumb-line-provenance[pandas]"` /
`[numpy]`); ADR-0013. Declare the source when wrapping: `source` is required
(since v0.12.0, #177) and `confidence` defaults to `'none'`. A wrapper built
without `source=` raises `ValueError`, as `make_meta` does. Operations outside
the combinators work on `.value` and drop provenance until re-wrapped.

### `PlumbDataFrame(value, source=, confidence=, **meta)` / `PlumbArray(value, source=, confidence=, **meta)`

Wraps a pandas `DataFrame` / numpy array. `.value` is the wrapped object,
`.meta` the envelope (`.meta_of()` returns it), `.audit()` runs `audit_meta`.

### `plumb_derive(inputs, fn, **meta_override)`

The general combinator in both modules: applies `fn` to the unwrapped inputs
and returns a wrapper whose envelope follows the combination law.

### `plumb_concat(objs, **kwargs)` / `plumb_merge(left, right, **kwargs)`

`pd.concat` / `DataFrame.merge` with taint propagated (`frames`).

### `plumb_concatenate(objs, **kwargs)` / `plumb_stack(objs, **kwargs)`

`np.concatenate` / `np.stack` with taint propagated (`arrays`).

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
| `provenanceVersion` | `provenance_version` | stamped | integer | Wire version the envelope was built under (SPEC §5b) |

Optional fields are **absent** (not `null`/`undefined`) when they have no
value — absence means "unknown" and is distinct from any present value.

Each lineage **step** records:

| Field | Type | Description |
|---|---|---|
| `id` | string `"sha256:<12 hex>"` | Content-addressed from the step's fields and input ids (SPEC §4; see `stepId`) |
| `of` | `"input"` | Step kind (currently always `"input"`) |
| `source` | `STATUS` enum | Source of this input |
| `confidence` | `CONFIDENCE` enum | Confidence of this input |
| `derivedFromMock` | boolean | Mock taint of this input |
| `confidenceScore` | number `[0,1]` | Numeric confidence (when present on input) |
