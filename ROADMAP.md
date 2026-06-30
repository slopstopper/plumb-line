# Roadmap

Planned features for future versions, roughly ordered by adoption impact.

---

## Planned

### 1. Static lint for untagged output-producing functions

**Priority: high**

The provenance primitive is fully opt-in: a developer can write
`const result = a.value + b.value` and bypass taint propagation entirely. The
existing `plumb-line-audit` skill can catch this in review, but it is
LLM-probabilistic, not deterministic.

Add a static AST-level pass that identifies functions which *produce* a return
value but never call `mark` or `derive`. This inverts the model from opt-in to
opt-out: provenance is assumed required on output-producing functions, and
absence is a lint error.

Scope:
- JS: ESLint rule (extend `provenance-lint/`) that flags functions returning a
  value without a `mark`/`derive` call on the return path
- Python: extend `adapters/python/provenance_lint.py` with an equivalent AST
  visitor
- Update `primitives/conformance/` to cover the new checker condition
- Hook into `adapters/*/hooks/pre-commit-gate` so untagged outputs block commit

---

### 2. Ecosystem adapters for common data sources

**Priority: high**

Taint propagation in security tools works because common sources (HTTP
requests, user input, env vars) are pre-tagged — developers don't mark every
individual call. plumb-line currently requires manual instrumentation at every
call site, which is a steep on-ramp for data/ML teams.

Build thin wrappers that auto-tag values at the point of ingestion:

- **Python:** `pandas` adapter — `PlumbDataFrame` wraps a DataFrame with a
  provenance envelope; operations that combine frames propagate taint
  automatically via `combineProvenance`. Similar wrapper for `numpy` arrays.
- **Python:** `requests`/`httpx` adapter — responses tagged `source: real` or
  `source: fallback` based on status code / cache header.
- **JS:** `fetch` adapter — same pattern; tags the resolved value before
  returning to the caller.

Each adapter ships as an optional extra in the respective package so the zero-
dependency core is not affected.

---

### 3. IDE integration

**Priority: medium**

Real-time provenance feedback at development time would change the adoption
curve. Right now enforcement is at commit time (git hooks) or review time
(Claude skill). A developer writing code has no inline signal.

- **VS Code extension:** inline decorations showing the provenance envelope on
  a hovered variable; warning gutter icons for untagged outputs or tainted
  values flowing into exports
- **Language server protocol:** surface `auditMeta` violations as diagnostics
  so any LSP-capable editor benefits (JetBrains, Neovim, etc.)
- **Quick-fix:** code action to wrap an untagged return in `mark()`/`derive()`
  with a prompt for source + confidence

---

## Completed

See [CHANGELOG.md](CHANGELOG.md) for shipped work.
