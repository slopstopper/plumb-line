---
name: plumb-line-audit
description: Use when auditing a diff or repository against the plumb-line principles — finds laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, outputs lacking recorded lineage, and baseline drift with no explanation. Read-only: it reports, never auto-fixes.
---

# Audit against the plumb-line principles

REQUIRED READING FIRST: `reference/portable-principles.md` (plugin root).

Scope the audit to the diff if one is given, else the whole repo. For broad
sweeps, dispatch read-only subagents and keep only their findings.

## Check catalogue (each finding cites the principle it violates)

1. Laundered uncertainty (P3) — a value that lost its confidence/provenance as it flowed downstream; a mock/approximate value treated as clean truth.
   - If the project uses the plumb-line provenance primitive: flag code that hand-builds provenance metadata bypassing combineProvenance/derive, and any value given a clean source while derived from a tainted input. Runtime complement: auditMeta().
2. Boundary leak (P2) — an import or call crossing layers against the declared direction; symbolic/derived/mock logic inside the source-truth layer (P1).
3. Hardcoded prior (P5) — a magic number encoding a judgment call, not injected/versioned config.
4. Overstated maturity (P6) — code or docs claiming current/done for something partial/mock/planned.
5. Missing lineage (P8) — an output stored without the inputs needed to reproduce it.
   - If the project uses the provenance primitive: flag derived values that are never marked or carry no lineage; recommend asserting auditMeta(metaOf(value)) === [] in tests.
6. Unexplained drift (P9) — a changed golden-baseline value with no recorded reason.
7. Suppressed null result (spine) — a code path that cannot express "no structure/no effect/inconclusive".
8. Escaped fakery (P4) — mock/approximate/fallback/cached data that left its container: not labelled (e.g. missing a derivedFromMock-style marker), or flowing into an export/output path that should exclude it unless explicitly opted in.
9. Uncontracted output (P7) — a public output shape with no versioned, validated contract: missing a validator, a version constant, or a canonical key list.

## Method

- For each check, grep/read for the smell, then confirm by reading context — do
  not report on a keyword match alone.
- Default to under-claiming: if unsure a finding is real, mark it "needs review",
  not "violation".

## Report (audit format)

For each finding: file:line, the principle (Pn), one-line description, and a
suggested direction (not a patch). End with a one-line summary count. If the
repo is clean, say so plainly — a clean result is a valid result.
