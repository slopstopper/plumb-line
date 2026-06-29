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

- **Specification:** [`SPEC.md`](https://github.com/effythealien/plumb-line/blob/main/primitives/SPEC.md) (envelope schema version 1)
- **Model, law, examples:** [`README.md`](https://github.com/effythealien/plumb-line/blob/main/primitives/README.md)
- **License:** Apache-2.0

JavaScript parity package: `plumb-line-provenance` on npm.
