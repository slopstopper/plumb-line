<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.svg">
    <img src="docs/logo.svg" alt="" height="42" align="middle">
  </picture>
  &nbsp;plumb-line
</h1>

[![npm](https://img.shields.io/npm/v/plumb-line-provenance?logo=npm)](https://www.npmjs.com/package/plumb-line-provenance)
[![PyPI](https://img.shields.io/pypi/v/plumb-line-provenance?logo=pypi&logoColor=white)](https://pypi.org/project/plumb-line-provenance/)
[![CI](https://github.com/effythealien/plumb-line/actions/workflows/ci.yml/badge.svg)](https://github.com/effythealien/plumb-line/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/plumb-line-provenance?logo=python&logoColor=white)](https://pypi.org/project/plumb-line-provenance/)
[![Issues](https://img.shields.io/github/issues/effythealien/plumb-line)](https://github.com/effythealien/plumb-line/issues)
[![Socket](https://socket.dev/api/badge/npm/package/plumb-line-provenance)](https://socket.dev/npm/package/plumb-line-provenance)

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

**The provenance primitive** is a standalone library, independent of the plugin. Install it as `plumb-line-provenance` from npm or PyPI:

```bash
npm install plumb-line-provenance      # JavaScript
pip install plumb-line-provenance      # Python
```

Or copy `primitives/js/` or `primitives/python/` into your project and import from it directly — the modules carry a dual-import shim, so both styles work.

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

## Security

The provenance envelope is a trust claim, so plumb-line states plainly what it guarantees and what it does not. The [trust & threat model](docs/threat-model.md) defines the property worth defending (taint cannot be laundered through the public API), the actors it serves, and its honest non-guarantees — Python envelopes are tamper-*evident*, not tamper-*proof*. To report a vulnerability, see [`SECURITY.md`](SECURITY.md).

## Status

plumb-line ships the run-time provenance primitive with JS/Python parity, the three skills, and enforcement adapters for JavaScript/TypeScript and Python — published to npm and PyPI as `plumb-line-provenance` (the badges above track the current version; the [changelog](CHANGELOG.md) has the per-release detail). The primitive's envelope and law are pinned by a versioned [specification](primitives/SPEC.md) (envelope schema version 1) and a cross-language [conformance suite](primitives/conformance/). The deterministic adapters — boundary checks and the `no-provenance-bypass` static lint (JS + Python) — are validated against the worked fixtures in `examples/`, catching every planted violation with no false positives; see the [validation results](docs/validation-results.md). plumb-line is held to its own principles, too: the auditor is run on plumb-line's own code before each method-surface release, and the [dogfooding report](docs/dogfood.md) and validation results record what it finds — including its own false-positive rate, since an LLM audit is a review aid, not a gate. Planned: bootstrap wiring so host projects adopt the primitive automatically, and Go and Rust adapters.

## Feedback

Tried it on a real codebase? Use-case feedback is welcome — bug reports and false positives especially help.

- **Public** — open a [feedback issue](https://github.com/effythealien/plumb-line/issues/new?template=feedback.yml). Good for bugs, false positives, and use cases you can share openly.
- **Private** — testing on an internal or confidential codebase? Use the [private feedback form](https://effythealien.github.io/plumb-line/feedback.html); it goes straight to the maintainer.

Raw output and one concrete "it caught something we'd otherwise have shipped" beat polished prose. Let me know if I may quote you or name you as an early user.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
