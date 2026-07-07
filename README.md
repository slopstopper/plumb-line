<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.svg">
    <img src="docs/logo.svg" alt="" height="42" align="middle">
  </picture>
  &nbsp;plumb-line
</h1>

[![npm](https://img.shields.io/npm/v/plumb-line-provenance?logo=npm)](https://www.npmjs.com/package/plumb-line-provenance)
[![PyPI](https://img.shields.io/pypi/v/plumb-line-provenance?logo=pypi&logoColor=white)](https://pypi.org/project/plumb-line-provenance/)
[![CI](https://github.com/slopstopper/plumb-line/actions/workflows/ci.yml/badge.svg)](https://github.com/slopstopper/plumb-line/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/slopstopper/plumb-line/badge)](https://scorecard.dev/viewer/?uri=github.com/slopstopper/plumb-line)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13453/badge)](https://www.bestpractices.dev/projects/13453)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/plumb-line-provenance?logo=python&logoColor=white)](https://pypi.org/project/plumb-line-provenance/)
[![node: >=16](https://img.shields.io/node/v/plumb-line-provenance?logo=node.js&logoColor=white&label=node)](https://www.npmjs.com/package/plumb-line-provenance)
[![JS + Python](https://img.shields.io/badge/language-JS%20%2B%20Python-informational)](https://github.com/slopstopper/plumb-line)
[![zero deps](https://img.shields.io/badge/deps-0-brightgreen)](https://www.npmjs.com/package/plumb-line-provenance?activeTab=dependencies)
[![minzipped](https://img.shields.io/bundlephobia/minzip/plumb-line-provenance?label=minzipped&color=brightgreen)](https://bundlephobia.com/package/plumb-line-provenance)
[![Socket](https://socket.dev/api/badge/npm/package/plumb-line-provenance)](https://socket.dev/npm/package/plumb-line-provenance)

A plumb line measures true vertical by gravity alone; plumb-line does the same for a codebase, keeping it epistemically honest (including about what it doesn't know). It gives a repository a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and boundaries checked by machines (not *vibes*).

plumb-line is a small, standalone provenance library for JavaScript and Python, paired with a Claude Code plugin (four skills). The library enforces the discipline while your code runs; the skills enforce it when you review — and now when you fix — code. What it is building toward (**planned** — see [where this is going](#where-this-is-going)): an epistemic honesty layer for agent-built software, where every value, artifact, and agent-produced claim carries where it came from and how sure anyone should be.

## Who it's for

plumb-line is for builders whose outputs are claims, where a silent mistake can poison the whole stream — research and scientific software, data and ML, AI agents and analytics, or any codebase you've inherited and must now stand behind. It assumes that being confidently wrong is worse than being honestly uncertain, that "we don't know yet" is a shippable answer, and that a number without provenance is a liability. As agents write more of the code and more of the claims, "who produced this, from what evidence, and how sure were they" stops being a research-software nicety — plumb-line is built from that end.

## Two halves: run-time and review-time

plumb-line enforces the same discipline at two moments. The **provenance primitive** applies it at run time, through a small library that makes uncertainty propagate across your actual calculations, so a tainted value can't quietly become a clean one. The **skills** apply it at review time, by loading the principles, generating a ruleset, and auditing a diff before it lands. Use either half alone, or both.

## Install

**As a Claude Code plugin (recommended).** The repository is its own plugin marketplace from inside Claude Code:

```
/plugin marketplace add slopstopper/plumb-line
/plugin install plumb-line@plumb-line
```

The first command registers the repo as a marketplace; the second installs the four skills. **Then get oriented: run `plumb-line-method`** — it teaches the discipline in a few minutes and hands you straight into `plumb-line-bootstrap` when you're ready to set your project up. Updates come through `/plugin`. To install manually instead, clone the repository and point Claude Code at the plugin directory, or add it under `plugins` in your `.claude/settings.json`:

```bash
git clone https://github.com/slopstopper/plumb-line.git
```

**The provenance primitive** is a standalone library, independent of the plugin. Install it as `plumb-line-provenance` from npm or PyPI:

```bash
npm install plumb-line-provenance      # JavaScript
pip install plumb-line-provenance      # Python
```

Or copy `primitives/js/` or `primitives/python/` into your project and import from it directly — the modules carry a dual-import shim, so both styles work.

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

**plumb-line-remediate** — applies the findings from an audit report, opt-in and separate from the audit itself: mechanical fixes are applied with a diff shown per finding, judgment calls are proposed (defaulting to the weakest honest claim when unanswered), and every run ends in a remediation record. It may never resolve a finding by making the code *less* honest — a fix that clears a taint flag or invents a confidence to pass a gate is refused as `blocked`.

## Repository layout

| Path          | What's there                                                       |
| ------------- | ----------------------------------------------------------------- |
| `primitives/` | Run-time provenance library (JS + Python), the `SPEC.md`, and the conformance suite |
| `skills/`     | The four Claude Code skills — method, bootstrap, audit, remediate |
| `adapters/`   | Enforcement adapters — ESLint / import-linter boundaries, git hooks |
| `reference/`  | Portable principles and the ruleset template                      |
| `examples/`   | Worked clean / broken fixtures for JavaScript and Python          |
| `docs/adr/`   | Architecture decision records                                     |

## Design decisions

The durable architecture choices behind plumb-line are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Security

The provenance envelope is a trust claim, so plumb-line states plainly what it guarantees and what it does not. The [trust & threat model](docs/threat-model.md) defines the property worth defending (taint cannot be laundered through the public API), the actors it serves, and its honest non-guarantees — Python envelopes are tamper-*evident*, not tamper-*proof*. To report a vulnerability, see [`SECURITY.md`](SECURITY.md).

## Status

plumb-line ships the run-time provenance primitive with JS/Python parity, the four skills, and enforcement adapters for JavaScript/TypeScript and Python — published to npm and PyPI as `plumb-line-provenance` (the badges above track the current version; the [changelog](CHANGELOG.md) has the per-release detail). The primitive's envelope and law are pinned by a versioned [specification](primitives/SPEC.md) (envelope schema version 1) and a cross-language [conformance suite](primitives/conformance/). The deterministic adapters — boundary checks and the `no-provenance-bypass` static lint (JS + Python) — are validated against the worked fixtures in `examples/`, catching every planted violation with no false positives; see the [validation results](docs/validation-results.md). plumb-line is held to its own principles, too: the auditor is run on plumb-line's own code before each method-surface release, and the [dogfooding report](docs/dogfood.md) and validation results record what it finds — including its own false-positive rate, since an LLM audit is a review aid, not a gate. Everything beyond that is **planned**, not current — the [roadmap](ROADMAP.md) is the authoritative index.

## Where this is going

The long-run direction (status: **planned** — this section names intent, not shipped capability; the [roadmap](ROADMAP.md) tracks each item):

- **Deepen the promise.** Tooling for the last unimplemented principle — a golden-baseline CLI with lineage-attributed drift — plus CI-native enforcement (GitHub Action, SARIF, an adoption ratchet for legacy codebases), and runtime primitives that refuse and explain: an egress guard at output boundaries, human-readable lineage, a per-artifact trust summary.
- **Provenance across boundaries.** Today the taint guarantee holds inside one process; envelopes should survive serialization, file artifacts (provenance sidecars), and HTTP (a provenance-context header) — so honesty becomes a property of a *system*, not a function call.
- **Agent epistemic state.** The audit skill already reports its own coverage honestly — a traversal plan, a read/partial/not-read map, an honest denominator. The plan is to generalize that machinery into a spec any agent can adopt, and a convention for agent-produced claims and code to carry provenance envelopes. In a world where agents produce most code and most analysis, "who claimed this, based on what, and how sure were they" is basic infrastructure; plumb-line builds it from the epistemic-honesty end.

## Contributing & governance

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for how to
open an issue or PR, and [GOVERNANCE.md](GOVERNANCE.md) for how the project is
run (decision-making, roles, and continuity). Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Feedback

Tried it on a real codebase? Use-case feedback is welcome — bug reports and false positives especially help.

- **Public** — open a [feedback issue](https://github.com/slopstopper/plumb-line/issues/new?template=feedback.yml). Good for bugs, false positives, and use cases you can share openly.
- **Private** — testing on an internal or confidential codebase? Use the [private feedback form](https://effythealien.github.io/plumb-line/feedback.html); it goes straight to the maintainer.

Raw output and one concrete "it caught something we'd otherwise have shipped" beat polished prose. Let me know if I may quote you or name you as an early user.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
