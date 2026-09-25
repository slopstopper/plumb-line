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
  script does not touch it. On any change to it, `scripts/check_version_prose.py`
  fails CI if a live doc still states the old wire version, and diffs the
  conformance badge against `report.mjs --badge`. It runs on every PR, so a
  stale copy surfaces at the PR that introduces it rather than at the tag
  ([#160](https://github.com/slopstopper/plumb-line/issues/160)).

**When to release.** Cut a release whenever a correctness, integrity or
security fix, or a user-facing feature, lands on `main` and affects the
published packages or plugin. Merging publishes nothing, so fixes left
unreleased stay unshipped: the F1–F3 integrity fixes of 0.2.0 sat behind a
stale tag for about 30 commits. Docs and chore changes can ride the next
release. Pre-1.0 SemVer: a breaking change or a feature bumps the minor; a
fix-only release is a patch.

## Steps

1. **Decide the number and verify milestone closure** (SemVer, per *When to release* above).
   Check what's unreleased: `git log --oneline "$(git describe --tags --abbrev=0)"..main`.
   
   **Crucial:** Before proceeding, verify the GitHub milestone for this version:
   ```
   gh api repos/slopstopper/plumb-line/milestones -q '.[] | select(.title | contains("'$VERSION'")) | {title, open_issues, closed_issues}'
   ```
   
   **All issues in the milestone must be either closed or explicitly reassigned to a later milestone.** An open issue in a closed milestone means planned work was deferred without being tracked. Open the milestone on GitHub and either:
   - **Close the issue** if it shipped
   - **Move it to the next version milestone** with a note if deferred (and file an `audit-deferral` issue if a finding)
   - **Re-open it to clarify** if the status is unclear
   
   Do not close the version milestone with open issues remaining. This gate prevents the [plumb-line principle](reference/portable-principles.md) P6 (maturity vocabulary) violation of overstating completion.
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
   fails *before* publishing. Then it runs the full suite and publishes,
   opens a `Content draft due: v<version>` issue, and pings
   [slopstopper.org](https://github.com/slopstopper/slopstopper.org) to
   resync its version pills and writing list. The ping needs the repository
   secret `SITE_DISPATCH_TOKEN`: a fine-grained PAT scoped to
   `slopstopper/slopstopper.org` with **Contents: read and write**. Without
   it the step logs "skipping ping" and the site catches up on its daily
   sync.
7. **Draft the release write-up.** One short piece per release, drafted from
   what actually shipped, under [`docs/content/TEMPLATE.md`](docs/content/TEMPLATE.md)
   and its four gates (audit, language standard, disclosure, venue courtesy). Source
   material is the CHANGELOG section, the harness record in
   `docs/validation-results.md`, the dogfood section, and the closed
   milestone. Open it as a PR that closes the draft-due issue; the owner
   edits and approves by merging. After the merge, render the approved piece
   where readers already look, per the template's Publishing section: embed
   it in the GitHub release body above the generated notes. The site's
   writing list is generated from `docs/content/` on the next sync, so the
   merge is the publish step; no site PR is needed. Update the README's "It audits itself" and
   harness paragraphs to the new release's numbers in the same PR — both
   cite a specific release and go stale otherwise (the v0.11.0 write-up PR
   is where this step was added, after exactly that staleness).
8. **Update your own plugin install.** The plugin version bump makes the
   release *available*; installing it is manual. Run `claude plugin list` to
   find the installed name, `plumb-line@<marketplace>`. `<marketplace>` is the
   `name` in the manifest of the marketplace you installed from: `plumb-line`
   for this repository (the README's path), `slopstopper` for
   `slopstopper/marketplace`. Then run
   `claude plugin update plumb-line@<marketplace>` and restart Claude Code.
   The owner's install once sat at 0.7.3 with 0.9.0 released
   ([#295](https://github.com/slopstopper/plumb-line/issues/295)).

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
