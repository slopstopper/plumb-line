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
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Software can calculate something correctly and still be wrong about what it knows. A stubbed service answers "success" and the test suite goes green. A field nobody could verify gets a guessed value and flows into a report. A fallback meant for local development ships. None of these fail loudly. Each one passes through the code until the final number looks as authoritative as everything around it.

plumb-line keeps that from happening quietly. It wraps a value with a record of where it came from and how far to trust it, and keeps that record attached as values combine. A result that leans on a mock or a guess says so, and that mark cannot be cleared on the way through. The rule underneath all of it is small: combining values can keep or lower their standing and can never raise it. A program cannot manufacture stronger evidence than it was given. That rule is written down as the [combination law](primitives/SPEC.md#3-the-combination-law), and it looks like this in practice:

```js
const base  = mark(1000, { source: "real", confidence: "high" });
const rate  = mark(1.25, { source: "mock", confidence: "low" });
const total = derive([base, rate], (a, r) => a * r);

total.derivedFromMock; // true   inherited from rate, and impossible to clear
total.confidence;      // 'low'  only as certain as the weakest input
```

`mark` labels a value with where it came from and how much to trust it. `derive` runs your own function on the values and carries the labels through, always keeping the weakest. The library never does the arithmetic for you and never changes a value. It only keeps the labels honest as values combine.

## It has already happened

Three documented public incidents, reconstructed as postmortems, each with a runnable demo (`examples/incident-*/`) in two versions, one without provenance and one with it, so you can run both and compare what they print:

- [The server that reported success for dead tools](docs/postmortems/mock-toolserver.md): stub tools returned success-shaped payloads; three audits of the same project produced three different numbers for how much of it was fake, because mockness wasn't machine-readable.
- [The plane that thought its passengers were children](docs/postmortems/loadsheet.md): a category guessed from an honorific entered a takeoff-mass calculation indistinguishable from a category actually known (AAIB serious incident, 2020).
- [The retraction that started as a sign flip](docs/postmortems/signflip.md): an unversioned processing script inverted published protein structures; five papers retracted, because no stored conclusion could say which code produced it.

Different domains and different mechanisms, with one pattern underneath: a value that forgot where it came from was combined into a claim someone acted on. plumb-line exists to make that class of failure visible and harder to launder. None of the postmortems claims it would have prevented the incident; each shows where the lost status would have been visible.

## You probably want this if

- **AI agents write or modify your code.** An agent that stubs a dependency to get a test green has no way to tell you, weeks later, that the number on the dashboard rests on that stub.
- **Mocks, fixtures, fallbacks, inferred values, synthetic data or hand-entered assumptions** exist anywhere between an input and an output.
- **Your outputs make claims.** A figure in a paper, a risk score, a forecast, a "safe to proceed": anything a person will act on.
- **You need to know what evidence supports a result**, as well as what the result is.

These symptoms cluster in research and scientific code, data and ML pipelines, agent-built systems, and any codebase you inherited and now have to stand behind.

You probably don't need the run-time layer if your app reads a trusted database and shows what it finds. The [fit map](reference/fit-map.md) says so plainly when that is the answer, and the review-time checks still apply to any codebase.

## Two layers

**Run time.** A small library, the provenance primitive, for JavaScript and Python with no dependencies, published as `plumb-line-provenance` on npm and PyPI. It is the `mark` and `derive` above: provenance travels with values through your own code.

**Review time.** Checks that read a repository or a diff for places where uncertainty, mocks, assumptions or unsupported claims have been laundered. Five Claude Code skills carry the judgment side: `plumb-line-audit` reviews a change or a repository with an LLM, its opt-in companion `plumb-line-remediate` applies the findings, and `plumb-line-adopt`, `plumb-line-method` and `plumb-line-bootstrap` route, teach and set up. Three of the five never write to your code, and the other two write only when you say yes. The deterministic side is ESLint and import-linter rules and git hooks that `plumb-line-bootstrap` installs, and a [GitHub Action](ACTION.md) that runs them in CI and reports in SARIF, the format GitHub's code-scanning tab reads.

Use either layer alone, or both. Adopt applies the fit map; bootstrap offers the library only at the call sites your own answers name, and only on an explicit yes.

## What is deterministic, and what is not

The provenance primitive and its propagation rules are deterministic. If a derived value depends on tainted input (an input carrying the mock flag from the example above), the taint propagates by specified rules, and a cross-language [conformance suite](primitives/conformance/) holds the JavaScript and Python implementations to identical behaviour, case by case. The enforcement adapters and the Action are deterministic too: a boundary rule either fires or it does not. The [validation results](docs/validation-results.md) record the adapters catching every planted violation with no false positives, the boundary break and the four bypass patterns in both languages. This repository's own CI runs the Action against the same fixtures for the boundary checks; the remaining capabilities are proven by unit tests over recorded tool output, and [ACTION.md](ACTION.md) grades each one.

The audit and remediate skills are different. They use an LLM as a review assistant, so plumb-line treats them as probabilistic components whose miss rate has to be measured. Before a release that touches them, the [release harness](docs/release-harness.md) runs blind validation: fixtures with planted violations and the answer keys withheld, at least two independent auditors on every fixture with violations planted, and a missed violation blocks the release until it is fixed and re-run, or a maintainer records a written waiver in the results. Calibration mistakes, false positives included, stay in the record.

## It audits itself

Before each release that changes the audit skill or the principles it applies, plumb-line runs its own audit skill over its own code and records what it found in the [dogfooding report](docs/dogfood.md). Findings are classified, fixed where the fix is right, and otherwise deferred to tracked issues; false positives stay in the record. A run that finds nothing still gets a dated section saying so. The line the project holds itself to: "the auditor found no problem" is never treated as proof that no problem exists.

## What plumb-line does not claim

- It does not prove that a value marked `real` is true. It records what the code claimed about the value and keeps that claim from being upgraded.
- It does not stop a source from lying, or a developer from marking a mock as real. The lint rules make bypasses visible; they cannot make them impossible.
- It does not make the LLM auditor infallible. Misses and false positives are measured and recorded, and the deterministic checks stand apart from it.
- It does not yet carry provenance across every boundary. The guarantee holds inside one process; envelopes, the record each marked value carries, do not yet survive serialization, file artifacts or HTTP transport, which are [planned](#where-this-is-going). The HTTP adapters tag responses on the way in, and the dataframe adapters carry taint only through their own combinators (`plumb_derive`, `plumb_concat`, `plumb_merge` and their numpy siblings), never through an ordinary pandas or numpy call; neither carries envelopes across the wire.
- Python envelopes are tamper-evident only: a caller holding one can edit it; what the library guarantees is that the edit cannot leak into a sibling envelope and that the inconsistency it leaves is detectable. The [threat model](docs/threat-model.md) says exactly what is defended.

What it targets is narrower: making it hard for software to turn uncertain information into something that looks certain without anyone noticing.

## Status

Current on `main`: the run-time primitive with JS/Python parity, published to npm and PyPI as `plumb-line-provenance`; the golden-baseline library and CLI (Principle 9, both languages, conformance-pinned); the five skills; enforcement adapters for JavaScript and Python; and the GitHub Action with SARIF output. The baseline and the Action are on `main` ahead of the v0.11.0 tag. The envelope and the combination law are pinned by a versioned [specification](primitives/SPEC.md) (schema version 2) and the conformance suite. A second lint, `require-provenance-output`, turns a trust-bearing function that returns a raw computation into a mechanical error inside a surface you declare ([ADR-0011](docs/adr/0011-enforcement-rule-scoping.md)); it is opt-in and a no-op until you draw that boundary.

Everything beyond what this section names is **planned**. The [roadmap](ROADMAP.md) is the index, the open issues are that roadmap in public ([#311](https://github.com/slopstopper/plumb-line/issues/311) explains the tracking), and the [changelog](CHANGELOG.md) has the per-release detail. Short write-ups of what shipped, drafted under their own audit gate, live in [docs/content/](docs/content/).

## Install

**As a Claude Code plugin.** The repository is its own marketplace from inside Claude Code:

```
/plugin marketplace add slopstopper/plumb-line
/plugin install plumb-line@plumb-line
```

Then run `plumb-line-adopt`. It looks at your repository and says which parts fit and what to run first. `plumb-line-method` teaches the discipline in a few minutes if you want the reasoning before the tooling; `plumb-line-bootstrap` sets a project up, and `plumb-line-audit` reviews a change. Updates come through `/plugin`. To install by hand instead, clone the repository and point Claude Code at the plugin directory.

**The library**, independent of the plugin:

```bash
npm install plumb-line-provenance      # JavaScript
pip install plumb-line-provenance      # Python
```

Or copy `primitives/js/` or `primitives/python/` into your project; the modules import either way.

**In CI.** Once bootstrap has installed enforcement, add the [GitHub Action](ACTION.md) so every pull request gets the same checks, with SARIF uploaded for code scanning through GitHub's own upload action, and no agent involved.

**Not using Claude?** The skills are host-neutral markdown over files and the library has no dependencies; [portable/README.md](portable/README.md) is the entry point that skips the plugin shell.

## Where this is going

Except where marked current, everything here is **planned**; the [roadmap](ROADMAP.md) tracks each item.

- **Deepen the promise.** The golden-baseline CLI with lineage-attributed drift and the GitHub Action are current on `main`. Next: an adoption ratchet for legacy codebases (no *new* untagged outputs against `main`), and run-time primitives that refuse and explain: an egress guard at output boundaries, human-readable lineage, a per-artifact trust summary.
- **Provenance across boundaries.** Envelopes that survive serialization, file artifacts and HTTP, so the guarantee that holds inside one process today holds across a whole system.
- **Agent epistemic state.** The audit skill already reports its own coverage: a traversal plan, a read/partial/not-read map, an honest denominator. The plan is to generalize that into a spec any agent can adopt, and a convention for agent-produced claims and code to carry provenance envelopes.

**The goal.** AI-assisted software is getting good at producing convincing answers and convincing artifacts. The harder problem is knowing what those outputs are entitled to claim. plumb-line is an attempt to put that boundary into software, so that uncertainty survives computation and a result does not become more trustworthy just because a program processed it.

## Reference

- [`primitives/README.md`](primitives/README.md): the model, the combination law, the envelope fields (`source`, `confidence`, `derivedFromMock`, `lineage`, and the optional `confidenceScore` and `weakestSource`), the runtime checker `auditMeta` / `audit_meta`, the golden-baseline API, and worked examples.
- [`primitives/SPEC.md`](primitives/SPEC.md): the envelope schema, version 2. [`primitives/conformance/`](primitives/conformance/): the case table both languages are held to.
- Ingestion adapters, optional extras that leave the core dependency-free: HTTP ([ADR-0012](docs/adr/0012-ecosystem-adapters-optional-deps-and-mapping.md)) tags `requests`/`httpx`/`fetch` responses by status and cache state; dataframe ([ADR-0013](docs/adr/0013-dataframe-adapters-explicit-combinators.md)) wraps pandas and numpy with explicit combinators.
- [`ACTION.md`](ACTION.md): the GitHub Action, its enforcement manifest and SARIF output. [`adapters/`](adapters/): the ESLint and import-linter rules and git hooks that bootstrap installs.
- [`reference/portable-principles.md`](reference/portable-principles.md): the nine principles and the maturity vocabulary. [`reference/fit-map.md`](reference/fit-map.md): whether the library fits your codebase, with worked profiles.
- [`docs/adr/`](docs/adr/): the architecture decisions, append-only.

| Path          | What's there                                                       |
| ------------- | ----------------------------------------------------------------- |
| `primitives/` | Run-time provenance library (JS + Python), the `SPEC.md`, and the conformance suite |
| `skills/`     | The five Claude Code skills: adopt, method, bootstrap, audit, remediate |
| `adapters/`   | Enforcement adapters: ESLint / import-linter boundaries, git hooks, the SARIF assembler |
| `reference/`  | Portable principles, the fit map, and the ruleset template        |
| `examples/`   | Worked clean / broken fixtures and the three incident demos       |
| `docs/adr/`   | Architecture decision records                                     |

### Security

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/slopstopper/plumb-line/badge)](https://scorecard.dev/viewer/?uri=github.com/slopstopper/plumb-line)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13453/badge)](https://www.bestpractices.dev/projects/13453)
[![Socket](https://socket.dev/api/badge/npm/package/plumb-line-provenance)](https://socket.dev/npm/package/plumb-line-provenance)

The provenance envelope is a trust claim, so the [trust & threat model](docs/threat-model.md) states what is defended (taint cannot be laundered through the public API), whom it serves, and what is not guaranteed. To report a vulnerability, see [`SECURITY.md`](SECURITY.md).

## Contributing & governance

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) for how to
open an issue or PR, and [GOVERNANCE.md](GOVERNANCE.md) for how the project is
run (decision-making, roles, and continuity). Participation is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Feedback

Tried it on a real codebase? Use-case feedback is welcome. Bug reports and false positives especially help.

- **Public**: open a [feedback issue](https://github.com/slopstopper/plumb-line/issues/new?template=feedback.yml). Good for bugs, false positives, and use cases you can share openly.
- **Private**: testing on an internal or confidential codebase? Use the [private feedback form](https://slopstopper.github.io/plumb-line/feedback.html); it goes straight to the maintainer.

Raw output and one concrete "it caught something we'd otherwise have shipped" beat polished prose. Let me know if I may quote you or name you as an early user.

The full name is **plumb-line provenance**. Unrelated projects called "plumbline" exist. This is the hyphenated one.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
