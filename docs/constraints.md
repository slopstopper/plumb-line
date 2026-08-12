# Global constraints — plumb-line

<!-- Canonical source for this repo's global constraints (connective
     tissue). Downstream docs — specs, plans, handover comments — copy
     the block below verbatim under a provenance line:

       constraints-copy: docs/constraints.md @ <commit sha>

     The drift gate (scripts/check-constraints-drift.sh) fails any copy
     that does not match this file at its pinned sha. Only the block
     between the markers is the copyable unit. -->

<!-- constraints:begin -->
- Release version is **0.8.0**, and the three manifests must always agree: `primitives/js/package.json`, `primitives/python/pyproject.toml`, `.claude-plugin/plugin.json`. Bump only via `node scripts/bump-version.mjs <version>`.
- `PROVENANCE_VERSION` is **2**, identical in `primitives/js/provenance.mjs` and `primitives/python/provenance.py`. It is the envelope wire version and moves independently of the release version; `bump-version` does not touch it.
- Published package name is **`plumb-line-provenance`**, identical on npm and PyPI.
- License is **Apache-2.0** in both manifests.
- Python floor is **`requires-python = ">=3.11"`**; the CI matrix tests **3.11 and 3.13**.
- Node floor as published is **`engines.node >= 16`**; CI tests **Node 20 only**.
- Report contracts are **report-format v3** and **remediation-format v1**, validated by `scripts/check_report_format.py`.
- JS envelopes are flat/spread and camelCase; Python envelopes are nested under `meta` and snake_case. Both must behave identically against `primitives/conformance/cases.json`.
- Releases are **tag-triggered only** (`.github/workflows/release.yml`). Never hand-publish; the tag must equal the manifests.
<!-- constraints:end -->

## Why these, and not others

The block holds constraints with **exact values that downstream documents
restate** — the ones where a stale copy in a spec or plan silently
contradicts the code. Rationale, history, and process live below the
markers and are never checked.

### The two floors that do not match

`engines.node >= 16` and a CI matrix of Node 20 only are **not the same
claim**, and the block records both rather than flattening them. The
published floor is what consumers are promised; the tested floor is what
is actually exercised. Node 16–19 are therefore supported-by-declaration
and unverified-by-test. Recorded as a known gap, not resolved here —
resolving it means either testing the floor or raising it, and that is a
release decision.

The Python pair does not have this problem: the floor is 3.11 and CI
tests 3.11, so the floor itself is exercised.

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
