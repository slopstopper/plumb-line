# ADR-0013: Dataframe adapters — explicit combinators, no proxying, Python-only

**Status:** Accepted · 2026-07-19

## Context

The ecosystem-adapters milestone (#92, ROADMAP #2) asks for provenance-carrying
wrappers over common data sources. The HTTP taggers shipped in v0.7.2 under
[ADR-0012](0012-ecosystem-adapters-optional-deps-and-mapping.md), which set the
pattern for "every later ecosystem adapter": a guarded optional extra, a
dependency-free core, and a shared cross-language parity fixture. v0.7.3 ships the
remaining half — pandas DataFrame and numpy array wrappers — and two of that
template's assumptions do not carry over unchanged, forcing explicit decisions.

**First**, how taint propagates. The primitive's `combine_provenance` law is
**value-agnostic** — it operates on metas, not on what they wrap — so `mark(df)`
and `derive([m1, m2], lambda a, b: pd.concat([a, b]))` already run the full law on
DataFrames today. A dataframe adapter is therefore mostly *ergonomics* over
existing machinery. The tempting maximal design is a wrapper that proxies the whole
pandas API (`__add__`, `.merge()`, `__getattr__`) and auto-propagates provenance
through every operation, so it "feels like a DataFrame." But pandas has hundreds of
methods, many returning scalars/Series/arrays, and — critically — **most operations
are not combinations**: a column select, a `groupby`, a sort produce a derived view
of *one* input, not a merge of several. Auto-attaching combination provenance to
them would fabricate lineage the data does not have.

**Second**, cross-language parity. ADR-0012's parity fixture exists because the
HTTP adapters live in both JS and Python. pandas and numpy have no JS equivalent,
so there is no second implementation to pin against.

**Third**, granularity. A frame has many columns of potentially different
provenance; tracking per-column or per-cell envelopes is a large, open-ended
design.

## Decision

### 1. Explicit combinators, not API proxying

`PlumbDataFrame` / `PlumbArray` are thin containers holding a `value` (the
frame/array) and a `meta` (a standard envelope from `make_meta`). Combination is
**explicit and named**:

- `plumb_derive(inputs, fn, **override)` — the general combinator: run `fn` on the
  unwrapped values, run `combine_provenance` on the metas, wrap the result. This is
  `marked.derive` typed for frames/arrays; it adds nothing to the law.
- `plumb_concat`/`plumb_merge` (pandas) and `plumb_concatenate`/`plumb_stack`
  (numpy) — ergonomic sugar over `plumb_derive` for the commonest joins.

The wrapper does **not** intercept, overload, or `__getattr__`-proxy arbitrary
pandas/numpy operations. To do anything the combinators don't cover, the user
operates on `.value` and re-wraps via `plumb_derive` at the combination point.

### 2. The user declares the source; there is no auto-classification

Unlike an HTTP response (whose status *is* a source signal), a raw DataFrame
carries no intrinsic provenance. The source is declared at wrap time
(`PlumbDataFrame(df, source="real")`). The adapter's value is propagation
ergonomics, not ingestion classification; no `read_csv`-style auto-tagging wrappers
ship.

### 3. Python-only, so no parity fixture (justified ADR-0012 deviation)

Because there is no second-language implementation, the shared parity fixture
element of ADR-0012 does not apply. The discipline instead is *not silently
dropping provenance through the wrapper API*, enforced by Python unit tests that
assert each combinator routes through `combine_provenance` and that the result
audits clean. This is a scoped deviation — the absence of a second language, not a
different mapping.

### 4. One envelope per frame

A `PlumbDataFrame` carries a single envelope for the whole frame. Per-column or
per-cell provenance is out of scope.

### 5. The rest of ADR-0012 holds

Guarded optional extras (`[pandas]`, `[numpy]`) with imports deferred to the point
of use; a dependency-free import surface; a no-extras CI guard proving the taggers
raise a clear install-hinting `ImportError`. Modules are named `frames.py` /
`arrays.py` — **not** `pandas.py`/`numpy.py`, which would shadow the real libraries
on the flat import path (the v0.7.2 `http.py`/stdlib-`http` collision, now a known
lesson; no shadow-guard `conftest.py` is needed because these names do not clash).

## Consequences

- **Correctness by construction.** Because combination is explicit, provenance is
  attached only where a combination actually happens. The rejected proxying design
  would have had to encode a correct combination-vs-derivation rule for every
  pandas method — the exact surface where correctness fails silently.
- **Almost no new provenance logic to get wrong.** The adapter reuses
  `combine_provenance` verbatim; the tests assert *routing through the law*, not new
  semantics. This is why a value-agnostic law was worth having.
- **Honest ergonomics, with a visible seam.** The cost is that operations outside
  the named combinators drop provenance until the user re-wraps — deliberately, so
  the combination point stays visible in the code rather than hidden behind a proxy.
- **#92 closes.** pandas + numpy complete the ecosystem-adapters milestone.
- **Precedent refined.** ADR-0012 remains the template; this ADR records that a
  *single-language* adapter drops the parity-fixture element (with unit-test
  discipline in its place), and that adapter module names must avoid shadowing the
  library they wrap.
- **Rejected alternatives on record:** full API proxying (fabricates lineage on
  non-combination ops; unbounded surface), auto-classification/`read_*` wrappers
  (no intrinsic source signal to classify; YAGNI), and per-column provenance
  (open-ended; deferred).
- **No wire impact.** Adapters call `combine_provenance`/`make_meta`;
  `PROVENANCE_VERSION` is untouched.
