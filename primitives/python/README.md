# plumb-line-provenance (Python)

A conservative provenance / confidence / lineage envelope with a
taint-propagation combination law: once any input is mock or low-confidence,
every value derived from it inherits that taint automatically — there is no
escape hatch that silently clears the flag.

```python
from plumb_line_provenance import mark, derive, meta_of, audit_meta

base = mark(1000, source='real', confidence='high')
rate = mark(1.25, source='mock', confidence='low')
total = derive([base, rate], lambda a, r: a * r)

total['meta']['derived_from_mock']  # True  — inherited from rate, cannot be cleared
total['meta']['confidence']         # 'low' — only as certain as the weakest input
audit_meta(meta_of(total))          # []    — internally consistent
```

You can also copy the module files directly into a project and import them flat
(`from marked import mark`); both styles work.

This package is the run-time half of [plumb-line](https://slopstopper.org/plumb-line/),
which also ships review-time audit skills and a GitHub Action that enforce the
same discipline on a codebase.

## Egress guard

`audit_meta` reports a problem after the fact; `guard` stops a value at an
output point (an export, a display, a publish) unless its envelope backs what
the output claims. It returns the value it was given, so the output point
unwraps it:

```python
from plumb_line_provenance import guard, unwrap, ProvenanceRefused

unwrap(guard(total))                          # raises: total derives from mock
unwrap(guard(total, no_mock=False))           # explicitly allowed
unwrap(guard(price, min_confidence='medium')) # refused below medium
```

A refusal raises `ProvenanceRefused` (a `ValueError`), whose `reasons` list
every reason; a display that should show "unavailable" instead catches it.
Mock is refused unless `no_mock=False` is passed (Principle 4's mock clause). The rest of Principle 4 is a source floor the
caller sets, e.g. `min_source='semiReal'` to refuse fallback and inferred data
without labelling it mock (#541). It fails closed: a value with no
envelope, a malformed one, or one the audit flags is refused, and taint and
confidence are judged from the whole lineage. A bad option is a `TypeError`,
never a refusal.

## Test fixtures (pytest)

Tests are where fake data is supposed to live; this makes the quarantine
explicit there (#123). The package registers a pytest plugin that adds no
hooks, fixtures or options. Decorate a fixture with `plumb_mock_fixture` (a drop-in for
`pytest.fixture`, keyword arguments included) and its value reaches the test
marked `source='mock'`; `assert_no_taint` fails a test when a golden output
still carries the taint. The check is `guard` with its defaults, so an
unmarked value fails too.

```python
from plumb_line_provenance import mark, derive
from plumb_line_provenance.pytest_plugin import plumb_mock_fixture, assert_no_taint

@plumb_mock_fixture
def rate():
    return 1.17                          # reaches the test marked mock

def test_price(rate):
    amount = mark(100, source='real', confidence='high')
    assert_no_taint(derive([amount, rate], lambda a, r: a * r))  # fails: mock reached it
```

`assert_tainted(output)` checks the taint did reach a value: it passes only
when `guard` refuses for mock taint, not for an unmarked or malformed value.
Marking is opt-in per fixture. A generator fixture's yielded value is marked
and its teardown still runs; a fixture that returns an already-marked value is
an error; async fixtures are not supported. The plugin loads at every pytest
start where the package is installed; `-p no:plumb_line_provenance.pytest_plugin`
turns it off.

## HTTP ingestion adapters (optional)

Auto-tag HTTP responses at ingestion. Install the extra for your client:

    pip install "plumb-line-provenance[requests]"
    pip install "plumb-line-provenance[httpx]"

```python
from plumb_line_provenance.http_adapter import tag_requests, tagged_get
from plumb_line_provenance import derive
import requests

resp = requests.get(url)
data = tag_requests(resp)                     # marked by status/cache
body = derive([data], lambda r: r.json())     # extract; taint propagates

data = tagged_get(url, timeout=5)             # fetch + tag in one call
```

Mapping (`source` = origin, `confidence` = freshness):

| HTTP condition        | source        | confidence |
| --------------------- | ------------- | ---------- |
| 2xx, fresh            | `real`        | `high`     |
| 2xx cached / `304`    | `real`        | `medium`   |
| 4xx / 5xx (no data)   | `unavailable` | `none`     |

Cache is detected best-effort from response headers (`Age > 0`, `X-Cache: HIT`,
`304`) and only lowers `confidence`, never `source`. (A `from_cache` attribute is
also honored if present — set by caching wrappers such as `requests-cache` — but
stock `requests`/`httpx` responses don't carry one, so header detection is the
path that fires for them.) The tagger never
emits `fallback` — that's for a value *you* substitute on error. The core
(`classify_response`) is dependency-free; the taggers guard-import their library
and raise a clear `ImportError` if the extra isn't installed.

> **The HTTP adapter is `http_adapter.py`.** Until 0.11.2 it was `http.py`, which
> shadowed the standard library's `http` package (and broke `requests`/`httpx`)
> whenever the directory was on `sys.path`. Flat copies import it as
> `http_adapter`; the installed package keeps `plumb_line_provenance.http` as an
> alias of `plumb_line_provenance.http_adapter` through 0.x (1.0 decision:
> [#429](https://github.com/slopstopper/plumb-line/issues/429)), so existing imports
> still work at run time. The alias is a runtime entry static type checkers cannot
> see; new code should import `http_adapter`.

## Dataframe adapters (optional)

Provenance-carrying wrappers for pandas / numpy, with explicit combinators that
propagate taint. Install the extra:

    pip install "plumb-line-provenance[pandas]"
    pip install "plumb-line-provenance[numpy]"

```python
from plumb_line_provenance.frames import PlumbDataFrame, plumb_concat, plumb_merge

base = PlumbDataFrame(df_a, source="real", confidence="high")
rate = PlumbDataFrame(df_b, source="mock", confidence="low")

total = plumb_concat([base, rate])          # runs pd.concat, propagates taint
joined = plumb_merge(base, rate, on="id")   # runs .merge, propagates taint

total.meta["derived_from_mock"]  # True — mock taint propagated, cannot be cleared
total.meta["confidence"]         # 'low' — only as certain as the weakest input
total.value                      # the underlying DataFrame
```

`plumb_derive([a, b], fn)` is the general combinator (any transform). numpy is the
same pattern: `from plumb_line_provenance.arrays import PlumbArray, plumb_concatenate, plumb_stack`.

You **declare** the `source` when you wrap (a raw frame carries no intrinsic
provenance — there is no auto-classification). `source=` is required, with no
default (since v0.12.0, #177): a wrapper built without it raises `ValueError`.
Operations outside the combinators
work on `.value` and drop provenance until you re-wrap via `plumb_derive` — the
combination point stays visible in your code (see [ADR-0013](https://github.com/slopstopper/plumb-line/blob/main/docs/adr/0013-dataframe-adapters-explicit-combinators.md)).
The core is dependency-free; the wrappers guard-import their library and raise a
clear `ImportError` if the extra isn't installed.

## Golden baseline

Pin a derived value *with its envelope* as a golden record, then refuse silent
drift: because lineage travelled with the value, a drift finding names which
field moved, not just that the number did. No extra needed.

```python
from plumb_line_provenance import assert_baseline, update

update('fx-rate', priced, because='initial pricing baseline')  # first run, or an accepted change
assert_baseline('fx-rate', priced)  # raises AssertionError, attributed, on drift
```

Records live in `.plumb-line/baselines/` unless you pass `dir=`. Accepting a new
state needs a non-empty `because`, stored in the record's append-only history.
`check` returns the report instead of raising; `list_baselines`, `show` and
`validate_baseline` inspect records. Inspect them from a shell with
`python -m plumb_line_provenance.baseline <list|show <name>|validate> [--dir D]`
(read-only: only running code carries the envelope, so it cannot check or
update).

Compared: each lineage step's trust fields and `of`, the lineage length, the
top-level trust fields and `basis`, then the value. `basis` counts as drift on
its own. Three drift classes are `not-implemented`: cross-step causality,
structural diffing inside a nested value, and float tolerance (comparison is
exact).

- **Specification:** [`SPEC.md`](https://github.com/slopstopper/plumb-line/blob/main/primitives/SPEC.md) (envelope schema version 2)
- **Model, law, examples:** [`README.md`](https://github.com/slopstopper/plumb-line/blob/main/primitives/README.md)
- **License:** Apache-2.0

JavaScript parity package: `plumb-line-provenance` on npm.
