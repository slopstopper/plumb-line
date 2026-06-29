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

- **Specification:** [`SPEC.md`](https://github.com/effythealien/plumb-line/blob/main/primitives/SPEC.md) (envelope schema version 1)
- **Model, law, examples:** [`README.md`](https://github.com/effythealien/plumb-line/blob/main/primitives/README.md)
- **License:** Apache-2.0

Python parity package: `plumb-line-provenance` on PyPI.
