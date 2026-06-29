# plumb-line

A plumb line measures true vertical by gravity alone; plumb-line does the same for a codebase, keeping it epistemically honest (including about what it doesn't know) through tooling rather than good intentions. It gives a repository a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and boundaries checked by machines, not trusted to hold.

Concretely, plumb-line is a small, standalone provenance library for JavaScript and Python, paired with a Claude Code plugin (three skills). The library enforces the discipline while your code runs; the skills enforce it when you review code.

## Who it's for

plumb-line is for builders whose outputs are claims — research and scientific software, data and ML, AI agents, analytics, or any codebase you've inherited and must stand behind. It assumes that being confidently wrong is worse than being honestly uncertain, that "we don't know yet" is a shippable answer, and that a number without provenance is a liability.

## Two halves: run-time and review-time

plumb-line enforces the same discipline at two moments. The **provenance primitive** applies it at run time, through a small library that makes uncertainty propagate across your actual calculations, so a tainted value can't quietly become a clean one. The **skills** apply it at review time, by loading the principles, generating a ruleset, and auditing a diff before it lands. Use either half alone, or both.

## The provenance primitive (run-time)

A JavaScript and Python library (`primitives/`) that wraps every value in a metadata envelope and combines values under a conservative-combination law: once any input is touched by mock or low-confidence data, every value derived from it inherits that taint automatically, with no escape hatch that silently clears the flag.

```js
const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);

total.derivedFromMock; // true   inherited from rate, and impossible to clear
total.confidence;      // 'low'  only as certain as the weakest input
```

The envelope carries `source`, `confidence`, `derivedFromMock`, and `lineage`, plus two optional resolution-bearing fields: a numeric `confidenceScore` (a finer-grained companion to the four-bucket ordinal) and a `weakestSource` (the least-trustworthy source anywhere in a value's ancestry). A runtime checker (`auditMeta` / `audit_meta`) flags laundering, over-claiming — ordinal and numeric — source over-claims, dropped taint, and unreproducible outputs.

The envelope and the law are a **specification, not just an implementation**: [`primitives/SPEC.md`](primitives/SPEC.md) defines envelope schema version 1, and a single cross-language [conformance suite](primitives/conformance/) pins JS and Python to identical behavior — so parity is enforced by data, not by prose. See [`primitives/README.md`](primitives/README.md) for the model, the law, and worked examples.

## The skills (review-time)

**plumb-line-method** — loads the [portable principles](reference/portable-principles.md): thesis, nine principles, maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.

**plumb-line-bootstrap** — interviews the builder, generates a domain-neutral ruleset, and installs enforcement adapters tailored to your project's structure and language.

**plumb-line-audit** — audits your diff or repository against the principles, surfacing laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, and outputs lacking recorded lineage.

## Repository layout

| Path          | What's there                                                       |
| ------------- | ----------------------------------------------------------------- |
| `primitives/` | Run-time provenance library (JS + Python), the `SPEC.md`, and the conformance suite |
| `skills/`     | The three Claude Code skills — method, bootstrap, audit           |
| `adapters/`   | Enforcement adapters — ESLint / import-linter boundaries, git hooks |
| `reference/`  | Portable principles and the ruleset template                      |
| `examples/`   | Worked clean / broken fixtures for JavaScript and Python          |
| `docs/adr/`   | Architecture decision records                                     |

## Install

**The provenance primitive** is a standalone library, independent of the plugin. Copy `primitives/js/` or `primitives/python/` into your project and import from it directly — both styles below work, and the modules carry a dual-import shim. Each language is also packaged as `plumb-line-provenance` for npm and PyPI (registry publication pending), so once published:

```bash
npm install plumb-line-provenance      # JavaScript  (publication pending)
pip install plumb-line-provenance      # Python      (publication pending)
```

**As a Claude Code plugin (recommended for the skills).** The repository is its own plugin marketplace. From inside Claude Code:

```
/plugin marketplace add effythealien/plumb-line
/plugin install plumb-line@plumb-line
```

The first command registers the repo as a marketplace; the second installs the three skills. Updates come through `/plugin`. To install manually instead, clone the repository and point Claude Code at the plugin directory, or add it under `plugins` in your `.claude/settings.json`:

```bash
git clone https://github.com/effythealien/plumb-line.git
```

## Design decisions

The durable architecture choices behind plumb-line are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Status

v0.1 ships the run-time provenance primitive with JS/Python parity, the three skills, and enforcement adapters for JavaScript/TypeScript and Python. The primitive's envelope and law are pinned by a versioned [specification](primitives/SPEC.md) (envelope schema version 1) and a cross-language [conformance suite](primitives/conformance/); both languages are packaged for npm and PyPI (registry publication pending). Both adapters are validated against the worked fixtures in `examples/`, catching every planted violation with no false positives; see the [validation results](docs/validation-results.md). plumb-line is held to its own principles, too — its auditor sniffs out its own smells; the [dogfooding report](docs/dogfooding.md) records what it found and fixed. Planned: an AST-level static lint rule for the primitive, bootstrap wiring so host projects adopt it automatically, and Go and Rust adapters.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
