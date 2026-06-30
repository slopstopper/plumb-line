# Releasing plumb-line

Releases are **tag-triggered**: pushing a `v*` tag runs
[`.github/workflows/release.yml`](.github/workflows/release.yml), which gates on
the full test suite and then publishes npm + PyPI (OIDC trusted publishing) and
creates the GitHub release. **Never `npm publish` / `twine upload` by hand** —
hand-publishing is what let the published `0.2.0` drift from `main`.

Two independent version numbers:

- **Release version** — the npm package, PyPI package, and Claude Code plugin.
  Lives in three manifests that must always agree:
  `primitives/js/package.json`, `primitives/python/pyproject.toml`,
  `.claude-plugin/plugin.json`. CI fails if they disagree.
- **`PROVENANCE_VERSION`** — the envelope wire format. Changes *only* on a
  breaking change to the metadata shape, independent of releases. The bump
  script does not touch it.

## Steps

1. **Decide the number** (SemVer; pre-1.0, a breaking change bumps the minor).
   Check what's unreleased: `git log --oneline "$(git describe --tags --abbrev=0)"..main`.
2. **Run the release harness if the method surface changed.** If the unreleased
   diff touches `skills/`, `reference/portable-principles.md`, `primitives/`, or
   `adapters/`, follow [`docs/release-harness.md`](docs/release-harness.md): a
   blind validation run (release-blocking — a missed planted violation stops the
   tag until fixed or waived in writing) plus a dogfood self-audit, both recorded
   as dated sections. Docs/chore-only releases skip this.
3. **Bump + promote notes in one step:**
   ```
   node scripts/bump-version.mjs 0.3.0
   ```
   This sets all three manifests in lockstep and promotes the CHANGELOG
   `## [Unreleased]` block to `## [0.3.0] — <date>`, leaving a fresh empty
   Unreleased and rewriting the compare links. Review the CHANGELOG diff and
   tidy the notes.
4. **Open it as a release PR**, let CI pass (the `Manifest versions agree` job
   confirms the three manifests match), and **merge to `main`**.
5. **Tag the merged commit** — the tag must equal the manifests, so tag *after*
   the bump PR is merged:
   ```
   git checkout main && git pull
   node scripts/check-versions.mjs v0.3.0   # local pre-flight: tag == manifests
   git tag v0.3.0 && git push origin v0.3.0
   ```
6. **Watch the Release workflow.** Its first step re-runs the guard
   (`check-versions.mjs <tag>` + a CHANGELOG `## [<version>]` check); if the tag
   doesn't match the manifests or the CHANGELOG has no section for it, the run
   fails *before* publishing. Then it runs the full suite and publishes.

## Releasing without a terminal

Every step above can happen from a phone — Claude runs the parts that need a
shell, the human taps the rest:

- **Bump + release PR** — ask Claude; it runs `bump-version.mjs`, which sets the
  manifests and promotes the CHANGELOG, and opens the PR.
- **Merge PRs** — tap *Merge* in the GitHub mobile app / web.
- **Tag + publish** — either: (a) tell Claude "publish" and it pushes the
  `v<version>` tag, or (b) in the GitHub app, **Releases → Draft a new release →
  create tag `v<version>` on `main` → Publish**. Both trigger the same workflow;
  the GitHub-release step is idempotent, so route (b) does not collide with it.

The tag push is the one irreversible, outward step (it publishes to npm + PyPI),
so Claude treats it as requiring an explicit human go-ahead — it will not tag on
its own.

## The guard that prevents drift

`scripts/check-versions.mjs` is the single source of truth for "are we
consistent": it asserts the three manifests agree, and (given a tag) that they
equal it. It runs in CI on every PR (no arg) and in the release workflow with the
pushed tag. A premature or mismatched tag fails the release instead of
publishing the wrong version — the failure mode that produced the `0.2.0`
divergence can no longer reach a registry.
