# Global constraints — plumb-line

**What this file does:** it is the one place this repo's exact values are
written down — version floors, wire version, package name, report
contracts. Other documents that need those values **copy the block below
instead of restating them**, and CI fails any copy that has been altered.

**How to use it, in three lines:**

1. Writing a spec, plan, or handover comment that states one of these
   values? Copy the whole block between the markers, verbatim.
2. Put a provenance line above it naming the commit you copied from:

   ```
   <!-- constraints-copy: docs/constraints.md @ 4ef30ce -->
   <!-- constraints:begin -->
   ...the copied block...
   <!-- constraints:end -->
   ```

3. Done. `scripts/check-constraints-drift.sh` runs in CI and compares your
   copy against this file *at that sha*.

The example above is inside a code fence deliberately: the gate treats a
marker inside a fence as a worked example rather than a real provenance
claim, so documentation like this does not register as a copy to check.

**What it catches:** a copy someone hand-edited, so a document states a
value this repo does not hold. **What it deliberately does not catch:** a
copy that is simply old — see "Sha-pinning" below for why, and where
staleness is caught instead.

If you are only reading values, read them here and do not copy anything;
the copy mechanism is for documents that must carry the values with them.

<!-- Canonical source for this repo's global constraints (connective
     tissue). Downstream docs — specs, plans, handover comments — copy
     the block below verbatim under a sha-pinned provenance line; the
     exact marker format is shown in the fenced example above.

     The drift gate (scripts/check-constraints-drift.sh) fails any copy
     that does not match this file at its pinned sha. Only the block
     between the markers is the copyable unit. -->

<!-- constraints:begin -->
- Release version is **0.8.0**, and the three manifests must always agree: `primitives/js/package.json`, `primitives/python/pyproject.toml`, `.claude-plugin/plugin.json`. Bump only via `node scripts/bump-version.mjs <version>`.
- `PROVENANCE_VERSION` is **2**, identical in `primitives/js/provenance.mjs` and `primitives/python/provenance.py`. It is the envelope wire version and moves independently of the release version; `bump-version` does not touch it.
- Published package name is **`plumb-line-provenance`**, identical on npm and PyPI.
- License is **Apache-2.0** in both manifests.
- Python floor is **`requires-python = ">=3.11"`**; the CI matrix tests **3.11, 3.12 and 3.13**.
- Node floor as published is **`engines.node >= 20`**; the CI matrix tests **Node 20 and 22**.
- Report contracts are **report-format v3** and **remediation-format v1**, validated by `scripts/check_report_format.py`.
- JS envelopes are flat/spread and camelCase; Python envelopes are nested under `meta` and snake_case. Both must behave identically against `primitives/conformance/cases.json`.
- Releases are **tag-triggered only** (`.github/workflows/release.yml`). Never hand-publish; the tag must equal the manifests.
<!-- constraints:end -->

## Why these, and not others

The block holds constraints with **exact values that downstream documents
restate** — the ones where a stale copy in a spec or plan silently
contradicts the code. Rationale, history, and process live below the
markers and are never checked.

### The two floors (resolved — both now exercised)

The published floor and the tested floor are **not the same claim**: the
first is what consumers are promised, the second is what CI actually
exercises. This file once recorded them diverging — `engines.node >= 16`
published while CI tested Node 20 only, leaving 16–19
supported-by-declaration and unverified-by-test. Resolved on `main` (rides the v0.9.0 release, GH #233) by
raising the floor rather than testing it (GH #233): the `./http` subpath
needs native `fetch` (Node ≥ 18) so the `>= 16` claim was partly false,
and the test runner cannot run below Node 20 — raising was the only
honest direction. Both pairs now match their matrices: Python floor 3.11
tested at 3.11, Node floor 20 tested at 20.

### Relationship to the existing checkers

Three gates already enforce parts of this block, and the drift gate does
not replace them:

| Gate | What it holds |
| --- | --- |
| `scripts/check-versions.mjs` | the three manifests agree with each other |
| `scripts/check_version_prose.py` | live docs do not state a stale wire version |
| `scripts/check-constraints-drift.sh` | copied constraint blocks match this file at their pinned sha |

The first two check the **code and its prose**. The drift gate checks
**copies of this block** in other documents. `check_version_prose.py` is
the narrower, hand-rolled ancestor of the same idea, applied to one
constraint; it stays as-is because it checks prose this block does not
carry.

### Sha-pinning, and what it deliberately does not catch

A copy pins the sha it was taken from, so a merged doc stays green when
this file later changes. That is intentional: the alternative — failing
every downstream doc the moment a constraint moves — makes the gate
something people route around.

The cost is that a **stale but internally consistent** pin passes CI. That
is the digest's concern, not CI's: aging pins surface in the sweep, the
same way aging deferrals do.
