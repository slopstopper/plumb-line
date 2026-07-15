# plumb-line-provenance (JavaScript)

A conservative provenance / confidence / lineage envelope with a
taint-propagation combination law: once any input is mock or low-confidence,
every value derived from it inherits that taint automatically — there is no
escape hatch that silently clears the flag.

```js
import { mark, derive, metaOf, auditMeta } from "plumb-line-provenance";

const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);

total.derivedFromMock; // true  — inherited from rate, cannot be cleared
total.confidence;      // 'low' — only as certain as the weakest input
auditMeta(metaOf(total)); // []  — internally consistent
```

You can also copy the `.mjs` files directly into a project and import them
relatively; both styles work.

## HTTP ingestion adapter (`plumb-line-provenance/http`)

Auto-tag `fetch` responses at ingestion. Native `fetch` — no dependency
(requires Node ≥ 18 or a browser).

```js
import { tagResponse, taggedFetch } from "plumb-line-provenance/http";
import { derive } from "plumb-line-provenance";

const resp = await fetch(url);
const data = tagResponse(resp);               // marked by status/cache
const body = derive([data], (r) => r.json()); // extract; taint propagates

const data2 = await taggedFetch(url);         // fetch + tag in one call
```

Mapping (`source` = origin, `confidence` = freshness): `2xx fresh → real/high`,
`2xx cached or 304 → real/medium`, `4xx/5xx → unavailable/none`. Cache is
best-effort (`Age > 0`, `X-Cache: HIT`, `304`) and lowers only `confidence`. The
tagger never emits `fallback`.

- **Specification:** [`SPEC.md`](https://github.com/slopstopper/plumb-line/blob/main/primitives/SPEC.md) (envelope schema version 2)
- **Model, law, examples:** [`README.md`](https://github.com/slopstopper/plumb-line/blob/main/primitives/README.md)
- **License:** Apache-2.0

Python parity package: `plumb-line-provenance` on PyPI.
