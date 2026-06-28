# plumb-line

Epistemic honesty, including the honesty of a null result, enforced by tooling and preserved across time rather than left to vibes. A plumb line finds true vertical by gravity alone. It asserts nothing; it measures. This collection helps a builder give any repository the same property: a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and rules enforced by machines rather than goodwill.

## Who it's for

plumb-line is for builders whose outputs are claims — where being confidently wrong is worse than being honestly uncertain. It fits research and scientific-software builders, data and ML practitioners, AI and agent builders, decision-support and analytics platforms, domain experts encoding methodology into software, solo builders and small teams without formal review processes, and anyone inheriting or auditing a codebase. If you'd rather ship "we don't know yet" than a confident guess, you treat auditability as a feature, and you're suspicious of numbers without provenance, this is for you.

## Two halves: review-time and run-time

plumb-line enforces the same discipline at two moments. The **skills** apply it at review time — loading the principles, generating a ruleset, and auditing a diff before it lands. The **provenance primitive** applies it at run time — a small library that makes uncertainty propagate through your actual calculations, so a tainted value can't quietly become a clean one. Use either half alone; together they close the gap between "the review said it was honest" and "the code stays honest while it runs."

## The skills (review-time)

**plumb-line-method** — loads the portable principles: thesis, nine principles, maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.

**plumb-line-bootstrap** — interviews your builder, generates a filled, domain-neutral ruleset, and installs enforcement adapters tailored to your project structure and language.

**plumb-line-audit** — audits your diff or repository against the principles, surfacing laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, and outputs lacking recorded lineage.

## The provenance primitive (run-time)

A JavaScript and Python library (`primitives/`) that wraps every value in a metadata envelope — `source`, `confidence`, `derivedFromMock`, `lineage` — and combines values under a conservative-combination law: once any input is touched by mock or low-confidence data, every value derived from it inherits that taint automatically, with no escape hatch that silently clears the flag. Laundering tainted data becomes structurally impossible rather than merely discouraged, and a runtime checker (`auditMeta` / `audit_meta`) flags laundering, over-claiming, dropped taint, and unreproducible outputs. See [`primitives/README.md`](primitives/README.md) for the model, the law, and worked examples.

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

Clone the repository:

```bash
git clone https://github.com/effythealien/plumb-line.git
```

Add plumb-line to Claude Code by pointing it at the plugin directory, or configure it in your `.claude/settings.json`. The provenance primitive is a standalone library — copy `primitives/js/` or `primitives/python/` into your project and import from it directly.

## Design decisions

The durable architecture choices behind plumb-line are recorded as ADRs in [`docs/adr/`](docs/adr/).

## Status

v0.1 ships the three skills, enforcement adapters for JavaScript/TypeScript and Python, and a run-time provenance primitive with JS/Python parity. Planned: an AST-level static lint rule for the primitive, bootstrap wiring so host projects adopt it automatically, and Go and Rust adapters.

## License

MIT — see [LICENSE](LICENSE).
