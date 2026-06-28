# plumb-line

Epistemic honesty — including the honesty of a null result — enforced by tooling and preserved across time, not vibes. A plumb line finds true vertical by gravity alone. It asserts nothing; it measures. This collection helps a builder give any repository the same property: a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and rules enforced by machines rather than goodwill.

## Who it's for

plumb-line is for builders whose outputs are claims — where being confidently wrong is worse than being honestly uncertain. It fits research and scientific-software builders, data and ML practitioners, AI and agent builders, decision-support and analytics platforms, domain experts encoding methodology into software, solo builders and small teams without formal review processes, and anyone inheriting or auditing a codebase. If you'd rather ship "we don't know yet" than a confident guess, you treat auditability as a feature, and you're suspicious of numbers without provenance, this is for you.

## The three skills

**plumb-line-method** — loads the portable principles: thesis, nine principles, maturity vocabulary, and the one-line test. Pure knowledge; takes no actions.

**plumb-line-bootstrap** — interviews your builder, generates a filled, domain-neutral ruleset, and installs enforcement adapters tailored to your project structure and language.

**plumb-line-audit** — audits your diff or repository against the principles, surfacing laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, and outputs lacking recorded lineage.

## Install

Clone the repository:

```bash
git clone https://github.com/effythealien/plumb-line.git
```

Add plumb-line to Claude Code by pointing it at the plugin directory, or configure it in your `.claude/settings.json`.

## Status

v1 delivers current enforcement adapters for JavaScript/TypeScript and Python. Go and Rust adapters are planned for future releases.

## License

MIT — see [LICENSE](LICENSE).
