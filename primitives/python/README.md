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

> **Flat-copy caveat for `http.py`:** the HTTP adapter file is named `http.py`. As
> an installed package it is `plumb_line_provenance.http` and is harmless, but if you
> copy it flat onto a directory that lands on `sys.path`, a top-level `import http`
> would shadow the standard library's `http` package and break `requests`/`httpx`
> (which import `http.client` internally). When copying it flat, import it under a
> package/private name rather than as bare `http`, or prefer the installed package.

## HTTP ingestion adapters (optional)

Auto-tag HTTP responses at ingestion. Install the extra for your client:

    pip install "plumb-line-provenance[requests]"
    pip install "plumb-line-provenance[httpx]"

```python
from plumb_line_provenance.http import tag_requests, tagged_get
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

- **Specification:** [`SPEC.md`](https://github.com/slopstopper/plumb-line/blob/main/primitives/SPEC.md) (envelope schema version 2)
- **Model, law, examples:** [`README.md`](https://github.com/slopstopper/plumb-line/blob/main/primitives/README.md)
- **License:** Apache-2.0

JavaScript parity package: `plumb-line-provenance` on npm.
