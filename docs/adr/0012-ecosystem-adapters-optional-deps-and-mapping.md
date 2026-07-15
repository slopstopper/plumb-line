# ADR-0012: Ecosystem adapters — optional-dependency pattern and the source-vs-freshness mapping

**Status:** Accepted · 2026-07-13

## Context

plumb-line's core is **zero-dependency** by construction (ADR-0001; no `dependencies`
in `pyproject.toml`, none in `package.json`) — a deliberate property that keeps the
provenance envelope a domain-neutral primitive anyone can adopt without pulling a
dependency tree. But the on-ramp goal (ROADMAP #2 / #92) is to lower adoption cost
for data/ML teams by **auto-tagging at ingestion** rather than hand-marking every
call site. The first such adapters wrap HTTP clients — Python `requests`/`httpx`
and JS `fetch` — tagging a response with a provenance envelope by its status and
cache state.

This forces two first-of-their-kind decisions:

1. **How to depend on third-party libraries without breaking the zero-dep core.**
   `requests` and `httpx` are real dependencies; `fetch` is native to JS. The
   adapter code must ship in the *published* packages (so `pip install
   plumb-line-provenance[requests]` works), yet `import plumb_line_provenance` must
   stay dependency-free for the many users who never touch HTTP.

2. **How an HTTP response maps onto the source ladder.** The envelope has two
   independent axes: `source` (the trust-tier of where a value came from) and
   `confidence` (how certain we are). A cache hit is the tension point — the data's
   *origin* is real, but its *freshness* is uncertain. #92's original wording
   ("tag `real` or `fallback` by status/cache") conflates the two.

Both decisions set precedent: the pandas/numpy wrappers (v0.7.3) and every later
ecosystem adapter will follow whatever pattern is chosen here.

## Decision

### 1. Optional extras with guarded imports, and a dependency-free classification core

- Adapters ship **inside the published packages** but the third-party import is
  **guarded and deferred to the point of use** — `import requests` lives inside
  `tag_requests`, not at module top. So `import plumb_line_provenance.http` and the
  pure `classify_response(...)` need no third-party library; only calling a specific
  tagger requires its specific dependency. A tagger invoked without its dep raises a
  clear `ImportError` naming the extra to install.
- The dependencies are declared as **optional extras**
  (`[project.optional-dependencies]` in Python; native `fetch` needs none in JS),
  so the default install stays zero-dependency and `[requests]`/`[httpx]` pull a dep
  only on request.
- The **mapping logic is a pure, dependency-free core** (`classifyResponse` /
  `classify_response`) that every adapter routes through after extracting
  `(status, headers, fromCache)` from its library's response type. This keeps the
  semantics in one place per language, testable with zero deps, and pinnable in a
  shared fixture.
- **A CI job runs the packages with the extras *absent*** to assert the core still
  imports and a tagger raises the documented `ImportError` — the regression guard
  that a stray top-level `import requests` would otherwise silently defeat.

### 2. `source` encodes origin, `confidence` encodes freshness — the tagger never emits `fallback`

The mapping keeps the two axes separate rather than collapsing HTTP quality onto
`source`:

| HTTP condition | source | confidence |
| --- | --- | --- |
| 2xx, fresh | `real` | `high` |
| 2xx, cached/stale | `real` | `medium` |
| 4xx or 5xx (no valid data) | `unavailable` | `none` |

- A **cache hit stays `real`** — its origin *is* the real upstream — and is
  downgraded only in `confidence`, because staleness is uncertainty, not a lesser
  origin. Downgrading the *source* of a cached-but-real value would misuse the axis.
- The tagger **never produces `source: fallback`.** `fallback` denotes a value a
  *caller* substitutes when the real one is unavailable; an error response is not a
  usable degraded value, so it is `unavailable`, not `fallback`. A caller who
  substitutes a default on error marks it `fallback` themselves.
- The mapping is a **cross-language parity contract**, pinned by a shared
  `http-cases.json` fixture both test suites load — the same data-not-prose
  mechanism the envelope law uses (`cases.json`).

## Consequences

- **The zero-dependency core survives.** Default installs pull nothing new; the
  "without extras" CI dimension proves it and fails loudly on regression.
- **One package, one version, one changelog.** Adapters live in the existing
  distributions rather than fragmenting into companion packages — simpler discovery
  and release machinery, at the cost of the published packages carrying adapter code
  most users won't import (kept cheap by the guarded-import design).
- **The mapping is honest and resolution-preserving.** Keeping `source` for origin
  and `confidence` for freshness means a stale cache hit is not misreported as a
  lesser source, and an error is not misreported as usable `fallback` data — the
  same conservatism the rest of the library enforces.
- **Precedent for all future adapters.** "Guarded optional extra + dependency-free
  core + shared parity fixture" is now the template for the v0.7.3 pandas/numpy
  wrappers and beyond; a later adapter that needs a genuinely different mapping must
  justify it against this ADR.
- **Rejected alternatives are on record:** separate companion packages (version-sync
  burden, fragmented discovery), bootstrap-copied templates (doesn't satisfy `pip
  install [extra]`), collapsing freshness/health onto `source` (conflates the two
  axes), and the literal `2xx=real / else=fallback` binary (loses the
  404-vs-503-vs-stale-cache resolution the library prides itself on).
- **No wire impact.** Adapters only *call* `mark`/`derive`; `PROVENANCE_VERSION`
  is untouched.
