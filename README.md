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
[![node](https://img.shields.io/node/v/plumb-line-provenance?logo=node.js&logoColor=white&label=node)](https://www.npmjs.com/package/plumb-line-provenance)
[![JS + Python](https://img.shields.io/badge/language-JS%20%2B%20Python-informational)](https://github.com/slopstopper/plumb-line)
[![zero deps](https://img.shields.io/badge/deps-0-brightgreen)](https://www.npmjs.com/package/plumb-line-provenance?activeTab=dependencies)
[![minzipped](https://img.shields.io/bundlephobia/minzip/plumb-line-provenance?label=minzipped&color=brightgreen)](https://bundlephobia.com/package/plumb-line-provenance)
[![Socket](https://socket.dev/api/badge/npm/package/plumb-line-provenance)](https://socket.dev/npm/package/plumb-line-provenance)

A plumb line measures true vertical by gravity alone. plumb-line does the same for a codebase: it keeps the code honest about what it knows and what it doesn't. A repository gets a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and boundaries checked by machines (not *vibes*).

The **skills** are a five-skill Claude Code plugin. Point them at any repository. Adopt, method, and audit install nothing in your code. Bootstrap and remediate write only when you say yes. The **provenance primitive** is a small, zero-dependency library for JavaScript and Python, published as `plumb-line-provenance` on npm and PyPI. It runs inside your calculations and makes uncertainty propagate. A tainted value cannot quietly become a clean one.

Start with either half. Bootstrap offers the primitive where the [fit map](reference/fit-map.md) says it belongs. The long-term aim, an epistemic honesty layer for agent-built software, is **planned**, not current; [where this is going](#where-this-is-going) tracks it.

## Who it's for

plumb-line is for builders whose outputs are claims: research and scientific software, data and ML, AI agents and analytics, or any codebase you inherited and must now stand behind. It assumes being confidently wrong costs more than being honestly uncertain, and that "we don't know yet" is a shippable answer. As agents write more of the code and more of the claims, "who produced this, and how sure were they" stops being a research-software nicety. plumb-line is built from that end.

If your app reads one database and displays what it finds, you probably don't need the run-time half. The [fit map](reference/fit-map.md) will tell you so plainly.

## The failure this prevents, three times over

Three reconstruction postmortems of documented public incidents, each with a runnable demo (`examples/incident-*/`) whose broken and instrumented variants print side by side:

- [The server that reported success for dead tools](docs/postmortems/mock-toolserver.md) — stub tools returned success-shaped payloads; three audits of the same project produced three different numbers for how much of it was fake, because mockness wasn't machine-readable.
- [The plane that thought its passengers were children](docs/postmortems/loadsheet.md) — a category guessed from an honorific entered a takeoff-mass calculation indistinguishable from a category actually known (AAIB serious incident, 2020).
- [The retraction that started as a sign flip](docs/postmortems/signflip.md) — an unversioned processing script inverted published protein structures; five papers retracted, because no stored conclusion could say which code produced it.

One sentence covers all three: a value that forgot where it came from was combined into a claim someone acted on.

## Two halves: run-time and review-time

plumb-line enforces the same discipline at two moments. At review time, the **audit** skill checks a diff or repository against the principles, and **remediate** applies the findings, opt-in. Around them, adopt routes, method teaches, bootstrap sets up. At run time, the **provenance primitive** makes uncertainty propagate across your actual calculations. Use either half alone, or both. Unsure whether your codebase needs the run-time half? The [fit map](reference/fit-map.md) answers with worked profiles, including a plain "you don't" where that is the truth.

## Install

**Not using Claude?** The skills are host-neutral markdown over files and the library installs from npm/PyPI with zero dependencies — [portable/README.md](portable/README.md) is the entry point that skips the plugin shell.

**As a Claude Code plugin (recommended).** The repository is its own plugin marketplace from inside Claude Code:

```
/plugin marketplace add slopstopper/plumb-line
/plugin install plumb-line@plumb-line
```

The first command registers the repo as a marketplace; the second installs the five skills. Then start:

1. Run `plumb-line-adopt`. It looks at your repository and tells you which parts fit and what to run first.
2. Run `plumb-line-method` if you want the reasoning first. It teaches the discipline in a few minutes.
3. Run `plumb-line-bootstrap` when you're ready to set the project up, and `plumb-line-audit` whenever you review a change.

Updates come through `/plugin`. To install manually instead, clone the repository and point Claude Code at the plugin directory, or add it under `plugins` in your `.claude/settings.json`:

```bash
git clone https://github.com/slopstopper/plumb-line.git
```

**The provenance primitive** is a standalone library, independent of the plugin. Install it as `plumb-line-provenance` from npm or PyPI:

```bash
npm install plumb-line-provenance      # JavaScript
pip install plumb-line-provenance      # Python
```

Or copy `primitives/js/` or `primitives/python/` into your project and import from it directly. The modules carry a dual-import shim, so both styles work.

## The provenance primitive (run-time)

A JavaScript and Python library (`primitives/`) that wraps every value in a metadata envelope and combines values under a conservative-combination law: once any input is touched by mock or low-confidence data, every value derived from it inherits that taint automatically, with no escape hatch that silently clears the flag.

```js
const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);

total.derivedFromMock; // true   inherited from rate, and impossible to clear
total.confidence;      // 'low'  only as certain as the weakest input
```

`mark` takes a value and attaches a label saying where it came from and how much to trust it. `derive` runs your own function on the values and carries the labels through, always keeping the weakest one. `metaOf` reads a value's label back, and `auditMeta` checks that a label is consistent. The library never does the arithmetic and never changes a value. It only keeps the labels honest as values combine.

The envelope carries `source`, `confidence`, `derivedFromMock`, and `lineage`, plus two optional resolution-bearing fields: a numeric `confidenceScore` (a finer-grained companion to the four-bucket ordinal) and a `weakestSource` (the least-trustworthy source anywhere in a value's ancestry). A runtime checker (`auditMeta` / `audit_meta`) flags laundering, ordinal and numeric over-claiming, source over-claims, dropped taint, and unreproducible outputs.

The envelope and the law are specified. [`primitives/SPEC.md`](primitives/SPEC.md) defines schema version 2, and a single cross-language [conformance suite](primitives/conformance/) pins JS and Python to identical behavior: parity is enforced by data, not prose. See [`primitives/README.md`](primitives/README.md) for the model, the law, and worked examples.

- **HTTP ingestion adapters** — auto-tag `requests`/`httpx`/`fetch` responses with provenance by status and cache state (optional extras; zero-dep core unaffected). See [ADR-0012](docs/adr/0012-ecosystem-adapters-optional-deps-and-mapping.md).
- **Dataframe adapters** — `PlumbDataFrame`/`PlumbArray` wrap pandas/numpy with provenance and propagate taint through explicit combinators (optional extras; zero-dep core unaffected). See [ADR-0013](docs/adr/0013-dataframe-adapters-explicit-combinators.md).

## The skills

**plumb-line-adopt** — the front door. Inspects your repository, then tells you which skills to run and, using the [fit map](reference/fit-map.md), whether the run-time primitives fit your codebase and what the smallest useful integration looks like in *your* code. Says "you don't need the primitives" plainly when that is the answer. Read-only; recommends and hands off, never edits.

**plumb-line-method** — loads the [portable principles](reference/portable-principles.md): thesis, nine principles, maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.

**plumb-line-bootstrap** — interviews the builder, generates a domain-neutral ruleset, and installs enforcement adapters tailored to your project's structure and language.

**plumb-line-audit** — audits your diff or repository against the principles, surfacing laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, and outputs lacking recorded lineage.

**plumb-line-remediate** — applies the findings from an audit report, opt-in and separate from the audit itself: mechanical fixes are applied with a diff shown per finding, judgment calls are proposed (defaulting to the weakest honest claim when unanswered), and every run ends in a remediation record. It may never resolve a finding by making the code *less* honest — a fix that clears a taint flag or invents a confidence to pass a gate is refused as `blocked`.

## Repository layout

| Path          | What's there                                                       |
| ------------- | ----------------------------------------------------------------- |
| `primitives/` | Run-time provenance library (JS + Python), the `SPEC.md`, and the conformance suite |
| `skills/`     | The five Claude Code skills — adopt, method, bootstrap, audit, remediate |
| `adapters/`   | Enforcement adapters — ESLint / import-linter boundaries, git hooks |
| `reference/`  | Portable principles, the fit map, and the ruleset template        |
| `examples/`   | Worked clean / broken fixtures for JavaScript and Python          |
| `docs/adr/`   | Architecture decision records                                     |

## Design decisions

The durable architecture choices behind plumb-line are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Security

The provenance envelope is a trust claim, so plumb-line states plainly what it guarantees and what it does not. The [trust & threat model](docs/threat-model.md) defines the property worth defending (taint cannot be laundered through the public API), the actors it serves, and its honest non-guarantees — Python envelopes are tamper-*evident*, not tamper-*proof*. To report a vulnerability, see [`SECURITY.md`](SECURITY.md).

## Status

plumb-line ships the run-time provenance primitive with JS/Python parity, the five skills, and enforcement adapters for JavaScript/TypeScript and Python, published to npm and PyPI as `plumb-line-provenance`. The badges above track the current version; the [changelog](CHANGELOG.md) has the per-release detail. The envelope and the combination law are pinned by a versioned [specification](primitives/SPEC.md) (schema version 2) and a cross-language [conformance suite](primitives/conformance/).

The deterministic adapters (boundary checks and the `no-provenance-bypass` lint, JS + Python) are validated against the worked fixtures in `examples/`: every planted violation caught, no false positives, results in [validation-results.md](docs/validation-results.md). A second lint, `require-provenance-output`, inverts the default inside a surface you declare: a trust-bearing function returning a provably raw computation becomes a mechanical error instead of something review must notice ([ADR-0011](docs/adr/0011-enforcement-rule-scoping.md)). It is opt-in and a no-op until you draw a boundary; `plumb-line-bootstrap` installs the config and resolves the surface when you accept the primitive offer ([#214](https://github.com/slopstopper/plumb-line/issues/214)).

**Held to its own principles.** The auditor runs on plumb-line's own code before each method-surface release, and the [dogfooding report](docs/dogfood.md) records what it finds, false positives included, because an LLM audit is a review aid, not a gate. Everything beyond what this section names is **planned**, not current. The [roadmap](ROADMAP.md) is the authoritative index, and the open issues are that roadmap made public — milestone-tracked work under semantic versioning, not bug debt ([#311](https://github.com/slopstopper/plumb-line/issues/311) explains the tracking method). Short write-ups of what shipped, drafted under their own audit gate, live in [docs/content/](docs/content/).

## Where this is going

The long-run direction. All of it is **planned**: this section names intent, not shipped capability, and the [roadmap](ROADMAP.md) tracks each item.

- **Deepen the promise.** Tooling for the last unimplemented principle (a golden-baseline CLI with lineage-attributed drift), CI-native enforcement (GitHub Action, SARIF, an adoption ratchet for legacy codebases), and runtime primitives that refuse and explain: an egress guard at output boundaries, human-readable lineage, a per-artifact trust summary.
- **Provenance across boundaries.** Today the taint guarantee holds inside one process. Envelopes should survive serialization, file artifacts (provenance sidecars), and HTTP (a provenance-context header), so honesty becomes a property of a *system*, not a function call.
- **Agent epistemic state.** The audit skill already reports its own coverage honestly: a traversal plan, a read/partial/not-read map, an honest denominator. The plan is to generalize that machinery into a spec any agent can adopt, and a convention for agent-produced claims and code to carry provenance envelopes. In a world where agents produce most code and most analysis, "who claimed this, based on what, and how sure were they" is basic infrastructure. plumb-line builds it from the epistemic-honesty end.

## Contributing & governance

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) for how to
open an issue or PR, and [GOVERNANCE.md](GOVERNANCE.md) for how the project is
run (decision-making, roles, and continuity). Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Feedback

Tried it on a real codebase? Use-case feedback is welcome. Bug reports and false positives especially help.

- **Public** — open a [feedback issue](https://github.com/slopstopper/plumb-line/issues/new?template=feedback.yml). Good for bugs, false positives, and use cases you can share openly.
- **Private** — testing on an internal or confidential codebase? Use the [private feedback form](https://slopstopper.github.io/plumb-line/feedback.html); it goes straight to the maintainer.

Raw output and one concrete "it caught something we'd otherwise have shipped" beat polished prose. Let me know if I may quote you or name you as an early user.

The full name is **plumb-line provenance**. Unrelated projects called "plumbline" exist. This is the hyphenated one.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
