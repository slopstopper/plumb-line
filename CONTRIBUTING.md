# Contributing

plumb-line keeps codebases epistemically honest, and it tries to hold itself to
the same standard. A few things worth knowing before you open a pull request.

This project follows a [Code of Conduct](CODE_OF_CONDUCT.md). By participating
you agree to abide by it. How the project is run — decision-making, roles, and
continuity — is described in [GOVERNANCE.md](GOVERNANCE.md).

## How to contribute

**Bug reports and questions** — open a [GitHub issue](https://github.com/effythealien/plumb-line/issues).
Include the component (`primitives/js`, `primitives/python`, an adapter, or a
skill), the version, and the shortest sequence of calls that reproduces the
problem. For suspected security issues, follow [SECURITY.md](SECURITY.md)
instead — do not open a public issue.

**Feature suggestions** — open an issue first. Describe the problem you are
trying to solve. This lets us discuss the design before anyone writes code, and
avoids wasted work if the direction doesn't fit the project.

**Pull requests** — for small, unambiguous fixes (typos, broken links, obvious
bugs) you can open a PR directly. For anything larger, open an issue first.
Every PR should:

- be focused on a single change,
- include a test that fails without the change (see [Running the tests](#running-the-tests)),
- pass the full CI suite locally before submission,
- have every commit signed off (DCO — see [Signing off your commits](#signing-off-your-commits-dco)), and
- update [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]` if it affects behaviour.

## Principles come first

Changes are judged against the [portable principles](reference/portable-principles.md)
the project enforces. If a change would have the tool launder uncertainty,
hardcode a prior, or overstate maturity, it will not land: the rules the audit
skill applies to your code apply to this repository too.

## Decisions are recorded

Durable architecture choices live as [ADRs](docs/adr/). If you are proposing a
decision rather than an implementation detail, add or amend an ADR alongside the
change. ADRs are append-only — a superseded decision is marked, not deleted.

## Coding style

**JavaScript** — ES modules throughout (`import`/`export`, no CommonJS except
where a tooling constraint requires `.cjs`). Use `const` by default, `let` when
reassignment is necessary, never `var`. Arrow functions for callbacks; named
function declarations for exported functions. No TypeScript in the primitives
or adapters; type information lives in JSDoc where useful.

**Python** — PEP 8. Snake case for functions and variables; `SCREAMING_SNAKE`
for module-level constants. Type annotations are welcome but not required. No
mutable default arguments.

When in doubt, match the style of the surrounding code. **Lint is enforced in
CI** — [ESLint](https://eslint.org) (recommended rules) for JavaScript and
[Ruff](https://docs.astral.sh/ruff/) (pyflakes + a pycodestyle subset) for
Python. There is no enforced auto-formatter, so keep diffs minimal.

## Running the tests

Enforcement is covered by real tests, not by assertions of correctness. Tests
also gate **statement coverage at ≥80%** (it fails the build below that):

```bash
# Provenance primitive
cd primitives/js && npm ci && npm test
cd primitives/python && python3 -m pytest

# Enforcement adapters (boundary hooks + provenance-bypass lint)
cd adapters/js && npm ci && npm test
cd adapters/python && python3 -m pytest
```

Lint the same way CI does:

```bash
cd primitives/js && npm run lint      # ESLint
cd adapters/js   && npm run lint
ruff check .                          # Python, from the repo root
```

New behaviour needs a test that fails without it. The
[validation results](docs/validation-results.md) record what the adapters are
expected to catch on the worked fixtures.

## Adding a language adapter

v0.1 ships JavaScript/TypeScript and Python; Go and Rust are planned. Parity
across languages matters more than breadth, so a new adapter should match the
existing [adapter contract](adapters/adapter-contract.md) rather than invent its
own shape.

## Releases

Merging to `main` doesn't publish anything; releases are cut deliberately from
version tags via the [release workflow](.github/workflows/release.yml). Shipped
changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## Signing off your commits (DCO)

Contributions are certified under the [Developer Certificate of Origin](DCO)
(DCO 1.1) — the same lightweight mechanism the Linux kernel uses. You certify
the DCO by adding a `Signed-off-by` trailer to each commit:

```
Signed-off-by: Your Name <your.email@example.com>
```

This is **not** a cryptographic signature and needs no keys — it is a plain text
line asserting you have the right to submit the change under the project's
[Apache-2.0](LICENSE) license. Git adds it for you with the `-s` flag:

```bash
git commit -s -m "fix: ..."
```

**Automatic sign-off (recommended).** Enable the bundled hook once per clone and
every commit is signed off for you — no need to remember `-s`:

```bash
git config core.hooksPath .githooks
```

The name and email come from your `git config user.name` / `user.email`, so make
sure those are set. CI enforces this: the **DCO** check
([`.github/workflows/dco.yml`](.github/workflows/dco.yml)) fails a PR if any
commit is missing a sign-off matching its author. To fix existing commits:

```bash
git rebase --signoff <base>..HEAD && git push --force-with-lease
```

## License of contributions

The project is licensed under [Apache-2.0](LICENSE). Unless you state otherwise,
any contribution you intentionally submit for inclusion is provided under the
same license, per Section 5 of Apache-2.0 — no separate agreement required. The
[DCO sign-off](#signing-off-your-commits-dco) records that agreement per commit.
