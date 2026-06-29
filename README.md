# plumb-line

A plumb line measures true vertical by gravity alone; plumb-line does the same for a codebase, keeping it epistemically honest (including about what it doesn't know) through tooling rather than good intentions. It gives a repository a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and boundaries checked by machines, not trusted to hold.

Concretely, plumb-line is a Claude Code plugin (three skills) paired with a small, standalone provenance library for JavaScript and Python. The skills enforce the discipline when you review code; the library enforces it while the code runs.

## Who it's for

plumb-line is for builders whose outputs are claims — research and scientific software, data and ML, AI agents, analytics, or any codebase you've inherited and must stand behind. It assumes that being confidently wrong is worse than being honestly uncertain, that "we don't know yet" is a shippable answer, and that a number without provenance is a liability.

## Two halves: review-time and run-time

plumb-line enforces the same discipline at two moments. The **skills** apply it at review time, by loading the principles, generating a ruleset, and auditing a diff before it lands. The **provenance primitive** applies it at run time, through a small library that makes uncertainty propagate across your actual calculations, so a tainted value can't quietly become a clean one. Use either half alone, or both.

## The skills (review-time)

**plumb-line-method** — loads the [portable principles](reference/portable-principles.md): thesis, nine principles, maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.

**plumb-line-bootstrap** — interviews the builder, generates a domain-neutral ruleset, and installs enforcement adapters tailored to your project's structure and language.

**plumb-line-audit** — audits your diff or repository against the principles, surfacing laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, and outputs lacking recorded lineage.

## The provenance primitive (run-time)

A JavaScript and Python library (`primitives/`) that wraps every value in a metadata envelope (`source`, `confidence`, `derivedFromMock`, `lineage`) and combines values under a conservative-combination law: once any input is touched by mock or low-confidence data, every value derived from it inherits that taint automatically, with no escape hatch that silently clears the flag.

```js
const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);

total.derivedFromMock; // true   inherited from rate, and impossible to clear
total.confidence;      // 'low'  only as certain as the weakest input
```

A runtime checker (`auditMeta` / `audit_meta`) flags laundering, over-claiming, dropped taint, and unreproducible outputs. See [`primitives/README.md`](primitives/README.md) for the model, the law, and worked examples.

## Repository layout

| Path          | What's there                                                       |
| ------------- | ----------------------------------------------------------------- |
| `skills/`     | The three Claude Code skills — method, bootstrap, audit           |
| `primitives/` | Run-time provenance library (JavaScript + Python)                 |
| `adapters/`   | Enforcement adapters — ESLint / import-linter boundaries, git hooks |
| `reference/`  | Portable principles and the ruleset template                      |
| `examples/`   | Worked clean / broken fixtures for JavaScript and Python          |
| `docs/adr/`   | Architecture decision records                                     |

## Install

**As a Claude Code plugin (recommended).** The repository is its own plugin marketplace. From inside Claude Code:

```
/plugin marketplace add effythealien/plumb-line
/plugin install plumb-line@plumb-line
```

The first command registers the repo as a marketplace; the second installs the three skills. Updates come through `/plugin`.

**Manually.** Clone the repository and point Claude Code at the plugin directory, or add it under `plugins` in your `.claude/settings.json`:

```bash
git clone https://github.com/effythealien/plumb-line.git
```

**The provenance primitive** is a standalone library, independent of the plugin install. Copy `primitives/js/` or `primitives/python/` into your project and import from it directly.

## Design decisions

The durable architecture choices behind plumb-line are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Status

v0.1 ships the three skills, enforcement adapters for JavaScript/TypeScript and Python, and a run-time provenance primitive with JS/Python parity. Both adapters are validated against the worked fixtures in `examples/`, catching every planted violation with no false positives; see the [validation results](docs/validation-results.md). plumb-line is held to its own principles, too — its auditor sniffs out its own smells; the [dogfooding report](docs/dogfooding.md) records what it found and fixed. Planned: an AST-level static lint rule for the primitive, bootstrap wiring so host projects adopt it automatically, and Go and Rust adapters.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
