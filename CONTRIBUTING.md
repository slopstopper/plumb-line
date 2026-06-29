# Contributing

plumb-line keeps codebases epistemically honest, and it tries to hold itself to
the same standard. A few things worth knowing before you open a pull request.

## Principles come first

Changes are judged against the [portable principles](reference/portable-principles.md)
the project enforces. If a change would have the tool launder uncertainty,
hardcode a prior, or overstate maturity, it will not land: the rules the audit
skill applies to your code apply to this repository too.

## Decisions are recorded

Durable architecture choices live as [ADRs](docs/adr/). If you are proposing a
decision rather than an implementation detail, add or amend an ADR alongside the
change. ADRs are append-only — a superseded decision is marked, not deleted.

## Running the tests

Enforcement is covered by real tests, not by assertions of correctness:

```bash
# Provenance primitive
cd primitives/js && npm install && npm test
cd primitives/python && python3 -m pytest

# Enforcement adapters
cd adapters/js && npm install && npm test
cd adapters/python/hooks && python3 -m pytest
```

New behaviour needs a test that fails without it. The
[validation results](docs/validation-results.md) record what the adapters are
expected to catch on the worked fixtures.

## Adding a language adapter

v0.1 ships JavaScript/TypeScript and Python; Go and Rust are planned. Parity
across languages matters more than breadth, so a new adapter should match the
existing [adapter contract](adapters/adapter-contract.md) rather than invent its
own shape.

## License of contributions

The project is licensed under [Apache-2.0](LICENSE). Unless you state otherwise,
any contribution you intentionally submit for inclusion is provided under the
same license, per Section 5 of Apache-2.0 — no separate agreement required.
