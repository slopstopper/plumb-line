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
2. Boundary leak (P2) — an import or call crossing layers against the declared direction; symbolic/derived/mock logic inside the source-truth layer (P1).
3. Hardcoded prior (P5) — a magic number encoding a judgment call, not injected/versioned config.
4. Overstated maturity (P6) — code or docs claiming current/done for something partial/mock/planned.
5. Missing lineage (P8) — an output stored without the inputs needed to reproduce it.
6. Unexplained drift (P9) — a changed golden-baseline value with no recorded reason.
7. Suppressed null result (spine) — a code path that cannot express "no structure/no effect/inconclusive".
8. Escaped fakery (P4) — mock/approximate/fallback/cached data that left its container: not labelled (e.g. missing a derivedFromMock-style marker), or flowing into an export/output path that should exclude it unless explicitly opted in.
9. Uncontracted output (P7) — a public output shape with no versioned, validated contract: missing a validator, a version constant, or a canonical key list.

## Method

Run two passes — they catch different failure modes, and some checks need both.

**Presence pass — things wrongly present.** A bad thing IS in the code: an upward
import (P2), a magic number (P5), an escaped/unlabelled mock (P4), a mock value
treated as clean truth (P3), overstated maturity (P6), a changed baseline value
(P9 drift). Grep/read for the smell, then confirm by reading context — never
report on a keyword match alone.

**Omission pass — things wrongly absent.** A good thing is MISSING, and an
absence has no smell to grep. Enumerate instead — and put the enumeration in your
report as a table, one row per output-producing function / public output shape,
one column per required field. This table is a REQUIRED artifact: the dropped
field is invisible unless you walk every output, and skipping the table is how
the omission gets missed. For each output ask —

- does it carry confidence + provenance where it influences a decision? (P3)
- does it record the lineage needed to reproduce it? (P8)
- does it have a versioned, validated contract? (P7)
- can it express a null / "no effect" / rejection outcome? (spine)
- is there a golden baseline pinning it? (P9)

The failure this pass exists to prevent is a `lineage`, `confidence`, or
`provenance` field silently dropped from ONE output while a declared rule (or a
sibling output) says it should be there — invisible to grep, caught only by the
table.

**Calibrate to adopted principles (governs the omission pass).** A principle is
_adopted_ when EITHER the project's declared ruleset/architecture requires it
(the primary signal — e.g. "service outputs are lineage-bearing", a declared
contract convention) OR sibling code already practices it (the fallback signal —
another output records lineage, other shapes ship a contract). An omission of an
adopted principle is a **violation** — and the declaration alone is enough: a
service output with no lineage violates a declared "services are lineage-bearing"
rule even if NO other output happens to carry lineage (the field may have been
removed from the only place it lived — its absence cannot also be its alibi).
Only where a principle is neither declared nor practiced anywhere — adopted
nowhere — do you refrain from flagging each output: report it ONCE as an advisory
adoption gap (a P6 maturity note), not as N violations. This keeps the audit
honest on small or early repos while still catching the dropped-field regression.

- Default to under-claiming: if unsure a finding is real, mark it "needs review",
  not "violation".

## Report (audit format)

For each finding: file:line, the principle (Pn), one-line description, and a
suggested direction (not a patch). End with a one-line summary count. If the
repo is clean, say so plainly — a clean result is a valid result.
