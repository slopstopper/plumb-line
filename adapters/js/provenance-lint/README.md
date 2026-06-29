# provenance-lint (JS)

A custom ESLint rule, `no-provenance-bypass`, that statically flags the
source-code patterns which launder taint or bypass the conservative-combination
law — the review-time complement to the runtime `auditMeta`. It enforces SPEC
PB1–PB4 (see [`primitives/SPEC.md`](../../../primitives/SPEC.md) §6).

It fires only at **resolved primitive call sites** (`mark`/`derive`/`makeMeta`/
`unwrap` imported from the primitive) and only on **literal** field values, so it
does not misfire on dynamic code or on unrelated functions of the same name.

## Usage (ESLint 9 flat config)

```js
const provenance = require("./provenance-lint"); // path to this dir

module.exports = [
  {
    files: ["src/**/*.{js,mjs}"],
    plugins: { "plumb-line": provenance },
    rules: { "plumb-line/no-provenance-bypass": "error" },
  },
];
```

`eslint-provenance.template.cjs` (one level up) is the bootstrap-installable
version of this config, with a `__GLOBS__` placeholder.

## The four patterns

- **PB1** — clean `source` asserted with `derivedFromMock: true` (laundering).
- **PB2** — `derivedFromMock: false` on a `derive` override (a no-op the law ignores).
- **PB3** — a clean `source` override on `derive` (relabeling a derived value).
- **PB4** — `mark(unwrap(x), …)` (re-marking via the import-bound `unwrap`, dropping lineage).

Each rule keys on an unambiguous form to stay **zero-false-positive**: a literal
`derivedFromMock: false` on a plain `mark` is the honest default (not flagged),
and a bare `x.value` could be any raw field (so only `unwrap(x)` is flagged).

Python parity: `adapters/python/provenance_lint.py`.

> Placement: this rule is library-coupled (it knows the primitive's API), unlike
> the domain-neutral boundary adapter. It lives here as enforcement for now and
> may move under `primitives/` in a future version.
