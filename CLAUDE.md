# CLAUDE.md — plumb-line

> Project instructions and conventions for Claude Code sessions (local and remote). Ensures consistent behavior and prevents scope drift across parallel jobs and distributed work.

plumb-line gives a repository **epistemic honesty enforced by tooling**: a clear source-truth layer, visible uncertainty, quarantined fakery, reproducible outputs, and boundaries checked by machines. Two halves: a **run-time provenance library** (JS + Python) and three **review-time Claude Code skills**. License: Apache-2.0.

## Layout

| Path | What's there |
| ---- | ------------ |
| `primitives/js`, `primitives/python` | The provenance library (the product). Published as `plumb-line-provenance` on npm / PyPI. |
| `primitives/SPEC.md` | Envelope schema **version 1** — the formal spec. |
| `primitives/conformance/cases.json` | Language-neutral case table; **the parity contract** (see below). |
| `skills/` | Three skills: `plumb-line-method`, `plumb-line-bootstrap`, `plumb-line-audit`. |
| `adapters/js`, `adapters/python` | Enforcement adapters — boundary git-hooks + `no-provenance-bypass` lint. |
| `reference/portable-principles.md` | The nine principles the project enforces (and is held to). |
| `examples/` | Worked `clean/` + `broken/` fixtures the adapters are validated against. |
| `docs/adr/` | Architecture Decision Records — **append-only**. |
| `docs/plans/`, `docs/specs/` | Internal build docs — **gitignored**, not published. |

## Commands — there is NO root test command

No root `package.json`. Each component is tested from its own directory (mirrors `.github/workflows/ci.yml`):

```bash
# Provenance primitive (the product)
cd primitives/js     && npm install && npm test     # vitest, 69 cases
cd primitives/python && python3 -m pytest -q         # 51 cases

# Enforcement adapters
cd adapters/js       && npm install && npm test
cd adapters/python   && python3 -m pytest -q

# Cross-language parity gate (run from repo root)
node primitives/conformance/report.mjs               # exits non-zero on divergence

# Example fixtures + real import-linter boundary (from repo root)
python3 -m pytest -q examples
```

Python CI test deps: `pip install pytest import-linter`. Node 20; Python 3.9 + 3.12 in CI.

## Parity is the central invariant

JS and Python must behave **identically**. `conformance/cases.json` is loaded by both `primitives/js/conformance.test.mjs` and `primitives/python/tests/test_conformance.py`.

**When you change combination/audit behavior:** change *both* implementations and add a row to `cases.json`. A divergence fails one suite — that's the point. Don't "fix" parity by editing prose in `PARITY.md`; fix the code or the case table.

## The two API shapes (easy to conflate)

| | JavaScript | Python |
| --- | --- | --- |
| Shape | **flat/spread**: `{ value, source, confidence, ... }` | **nested**: `{ 'value': ..., 'meta': {...} }` |
| Casing | `camelCase` (`derivedFromMock`) | `snake_case` (`derived_from_mock`) |
| Extract meta | `metaOf(x)` | `meta_of(x)` |
| Checker | `auditMeta(meta)` | `audit_meta(meta)` |

Modules carry a **dual-import shim** — they work both as a package and copied in-tree. The law: combine -> `derivedFromMock` = OR of inputs (never clears), `confidence` = weakest input, `source` = `"derived"`, `confidenceScore` = min *only if every input has one*, `weakestSource` = computed-only (cannot be hand-set).

## Versioning (two independent numbers)

- **Release version** lives in 3 manifests that must always agree: `primitives/js/package.json`, `primitives/python/pyproject.toml`, `.claude-plugin/plugin.json`. Bump in lockstep: `node scripts/bump-version.mjs <version>`. The plugin version is what triggers updates for installed users.
- **`PROVENANCE_VERSION`** (envelope schema / wire version) changes *only* on a breaking change to the metadata format — independent of releases. `bump-version` does **not** touch it.

## Releases — cadence & process

- **Cadence: ship when published code changes.** Cut a release whenever a correctness/integrity/security fix or a user-facing feature lands on `main` that affects the published packages or plugin — don't let those sit unreleased (the 0.2.0 lesson: F1–F3 integrity fixes were stuck behind a stale tag for ~30 commits). Pure docs/chore can wait and ride the next release.
- **SemVer (pre-1.0):** breaking → **minor**, feature → **minor**, fix-only → **patch**. (The release version and `PROVENANCE_VERSION` move independently — see Versioning.)
- **Method-surface releases run the harness.** Before tagging a release whose diff touches `skills/`, `reference/portable-principles.md`, `primitives/`, or `adapters/`, run `docs/release-harness.md` (blind validation + dogfood self-audit, recorded as dated sections). A validation FAIL — a missed planted violation — blocks the tag until fixed or waived in writing; dogfood findings follow fix-or-defer→issue.
- **Never hand-publish.** Releases are tag-triggered only (`.github/workflows/release.yml`); see `RELEASING.md`. Hand-publishing is what made 0.2.0 drift from `main`.
- **Tag after the bump PR merges, never before.** `node scripts/bump-version.mjs <v>` sets the 3 manifests in lockstep *and* promotes `CHANGELOG [Unreleased] → [<v>]`. The pushed tag must equal the manifests — `scripts/check-versions.mjs` enforces it in CI (every PR) and in the release workflow (before publish), so a premature/mismatched tag fails instead of publishing.
- **No local machine needed.** Claude runs the bump, opens the release PR, and pushes the tag; the human merges PRs (GitHub mobile/web) and gives an explicit "go" for the tag push — the one irreversible, outward step (publishes npm + PyPI).

## Conventions / gotchas

- **Held to its own principles.** Don't launder uncertainty, hardcode a prior, or overstate maturity in this repo's own code — the audit skill is applied here too. Use the maturity vocabulary (`current` / `planned`), not aspirational claims.
- **Deferred findings become issues.** When an audit/dogfood/review defers a finding (anything not fixed in-place), file it as a GitHub issue labeled `audit-deferral` (`gh issue create --label audit-deferral`) and link the issue from wherever it's tabled (e.g. `docs/dogfood.md`). A markdown table is where deferrals get silently dropped; the tracker is the enforcement.
- **ADRs are append-only.** Proposing a durable decision -> add/amend an ADR; a superseded decision is *marked*, not deleted.
- **Releases are deliberate.** Merging to `main` publishes nothing — see *Releases — cadence & process* above.
- **New behavior needs a failing test first.** Enforcement is proven by tests, not asserted.
- **Tamper-evident, not tamper-proof.** Python envelopes are tamper-*evident* only — see `docs/threat-model.md`. The defended property: taint cannot be laundered through the public API.
- **Background jobs:** `EnterWorktree` before editing tracked files (enforced). This CLAUDE.md is local-only, so it lives in the real working copy, not a worktree.
