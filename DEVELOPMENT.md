# Development — Technical discipline for plumb-line

This document records the non-negotiable technical rules that keep plumb-line honest. They apply to all contributors and all automation (CI, release workflows, background sessions).

## Parity is the central invariant

JavaScript and Python implementations must behave **identically**. This is enforced by machine:

- `primitives/conformance/cases.json` is the golden ruleset; both language implementations load it and validate against it
- Any divergence in behavior **fails the conformance suite** — that's the point
- When you change combination logic, audit behavior, or validator logic: change *both* implementations and add a conformance case
- Do not "fix" parity by editing prose in `PARITY.md`; fix the code or the case table

The conformance suite is run in CI on every PR. A divergence catches it before merge.

## Audit deferrals become tracked issues

When an audit (self-audit, dogfood, or code review) defers a finding — anything not fixed in place — it must become a GitHub issue with the `audit-deferral` label. This is the enforcement mechanism.

**Why:** A markdown table of deferred findings is silently dropped. The tracker makes the deferral visible and prevents it from falling through the cracks.

**Process:**
1. When a finding is deferred, file an issue: `gh issue create --label audit-deferral --title "..."` with a reference to where it was tabled (e.g., `docs/dogfood.md` section header or audit run date)
2. Link the issue from the deferral's source (the findings table or the CHANGELOG entry)
3. That issue is now part of the project's accountability

See [RELEASING.md](RELEASING.md) for how this affects version closure.

## Version closure: milestone completeness gate

Before bumping a release version, verify that the GitHub milestone is closed:

- All issues assigned to the milestone must be either **closed** (shipped) or **explicitly reassigned** to a later milestone (deferred)
- If an issue is deferred, it must have been moved to the next milestone *before the version bump*
- A release with open issues still assigned to its milestone overstates completion — a P6 (maturity vocabulary) violation

See [RELEASING.md](RELEASING.md) step 1 for the verification command.

## Two independent version numbers

**Release version** — the npm package, PyPI package, and Claude Code plugin. Lives in three manifests that must always agree:
- `primitives/js/package.json`
- `primitives/python/pyproject.toml`
- `.claude-plugin/plugin.json`

CI fails if they disagree (`scripts/check-versions.mjs` enforces it).

**`PROVENANCE_VERSION`** — the envelope wire format (SPEC version). Changes *only* on a breaking change to the metadata shape, independent of releases. The bump script (`bump-version.mjs`) does **not** touch it. A schema fix (conformance correction, not a breaking change) does not bump this version; a true wire format break (v1 → v2) does.

## No hand-publishing

Releases are **tag-triggered only** via `.github/workflows/release.yml`. The workflow gates on the full test suite, then publishes to npm + PyPI using OIDC trusted publishing.

**Never run `npm publish` or `twine upload` by hand.** Hand-publishing is what let v0.2.0 drift from `main`. The tag is the single source of truth.

See [RELEASING.md](RELEASING.md) for the full release process.

## Running tests — there is no root command

No root `package.json`. Each component is tested from its own directory:

```bash
# Provenance primitive (the product)
cd primitives/js     && npm install && npm test     # vitest, ~69 cases
cd primitives/python && python3 -m pytest -q         # ~51 cases

# Enforcement adapters
cd adapters/js       && npm install && npm test      # ~16 cases
cd adapters/python   && python3 -m pytest -q         # ~21 cases

# Cross-language parity gate (from repo root)
node primitives/conformance/report.mjs               # exits non-zero on divergence

# Example fixtures + import-linter boundary (from repo root)
python3 -m pytest -q examples
```

Python CI test deps: `pip install pytest import-linter`. Node 20; Python 3.11 + 3.13 in CI (floor is 3.11 — see [SUPPORT.md](SUPPORT.md)).

## Held to its own principles

This repository is audited by its own `plumb-line-audit` skill before method-surface releases. The audit applies the same portable principles to plumb-line's code that it applies to yours. See [docs/release-harness.md](docs/release-harness.md) and [docs/dogfood.md](docs/dogfood.md) for how findings are recorded and resolved.

Overstating what is done, what is known, or what is finished is exactly the failure mode plumb-line exists to prevent. This cuts both ways.
