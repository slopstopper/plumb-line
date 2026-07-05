---
name: plumb-line-audit
description: Use when auditing a diff or repository against the plumb-line principles — finds laundered uncertainty, boundary leaks, hardcoded priors, overstated maturity, outputs lacking recorded lineage, and baseline drift with no explanation. Read-only: it reports, never auto-fixes.
---

# Audit against the plumb-line principles

REQUIRED READING FIRST: `reference/portable-principles.md` (plugin root).
If this file cannot be read, stop immediately and report: "Cannot audit: `reference/portable-principles.md` is missing or unreadable. Do not proceed from memory — the principles file is the source of truth for this audit."

Scope the audit to the diff if one is given, else the whole repo. For broad
sweeps, dispatch read-only subagents and keep only their findings.

**Coverage honesty (emit a traversal plan first).** Before reading, list the
in-scope files — the diff's touched files, or the repo's source tree — and state
which you will read, sample, or skip. That list is the audit's **denominator**.
Track `read` / `partial` / `not-read` as you go and report it in the coverage map
(Report §4). On anything larger than a small diff you will NOT read every file;
say so up front rather than at the end. Never state or imply full coverage unless
every in-scope file is marked `read` — an unread file with no finding is *not* a
clean file, and claiming otherwise is the laundered-uncertainty / overstated-
maturity failure this audit exists to catch (P8 — State-first lineage, and the
honest-denominator discipline), turned on the audit itself.

## Check catalogue (each finding cites the principle it violates)

1. Laundered uncertainty (P3) — a value that lost its confidence/provenance as it flowed downstream; a mock/approximate value treated as clean truth.
   - If the project uses the plumb-line provenance primitive: flag code that hand-builds provenance metadata bypassing combineProvenance/derive, and any value given a clean source while derived from a tainted input. Runtime complement: auditMeta().
2. Boundary leak (P2) — an import or call crossing layers against the declared direction; symbolic/derived/mock logic inside the source-truth layer (P1).
3. Hardcoded prior (P5) — a magic number encoding a judgment call, not injected/versioned config.
4. Overstated maturity (P6) — code or docs claiming current/done for something partial/mock/planned.
5. Missing lineage (P8) — an output stored without the inputs needed to reproduce it.
   - If the project uses the provenance primitive: flag derived values that are never marked or carry no lineage; recommend asserting auditMeta(metaOf(value)) === [] in tests.
6. Unexplained drift (P9) — a changed golden-baseline value with no recorded reason.
7. Suppressed null result (spine) — a code path that cannot express "no structure/no effect/inconclusive". Confirmed only where rejection is a declared or practiced concern; where rejection is adopted nowhere, an always-accept/always-success stub is an advisory adoption gap, not a violation (see "Calibrate to adopted principles" below).
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
report as a table, one row per output-producing function / public output shape.
Give each question below its OWN column — do not collapse them. This table is a
REQUIRED artifact: the dropped field is invisible unless you walk every output,
and skipping the table is how the omission gets missed. For each output ask —

- does it carry **provenance** (where the value came from) where it influences a decision? (P3)
- does it carry **confidence** where it influences a decision? (P3)
- does it record **lineage** — the inputs needed to *reproduce* it (source, record/row count, field names, config/version used)? (P8)
- does it have a versioned, validated contract? (P7)
- can it express a null / "no effect" / rejection outcome? (spine)
- is there a golden baseline pinning it? (P9)

Provenance and lineage are SEPARATE columns and a present provenance string does
NOT satisfy lineage: a free-text `provenance` ("stub source: …") or a
`weights_version` answers *where from / which config*, but lineage answers *can I
regenerate this exact output* — which usually needs the record count, the field
names, and the source identity that a provenance string omits. If the
lineage-bearing layer's output has provenance but no field recording those
reproduction inputs, that is a missing-lineage (P8) violation, not a pass.

The failure this pass exists to prevent is a `lineage`, `confidence`, or
`provenance` field silently dropped from ONE output while a declared rule (or a
sibling output) says it should be there — invisible to grep, caught only by the
table. The most common miss is treating provenance-present as lineage-present;
the dedicated lineage column is what forces the check.

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

**The spine obeys this calibration too.** An always-`true` / always-success stub
(e.g. a `submitPayment` that can only return `accepted: true`) suppresses the
null/rejection outcome — but whether that is a **violation** or merely an
**adoption gap** turns on the same test. If rejection is declared in the
architecture or practiced by sibling code, the missing reject path is a confirmed
spine violation. If rejection is adopted nowhere — neither declared nor practiced
anywhere — a deliberate stub on a layer that never claims to reject is the
under-claim case: report it once as a `needs-review` advisory adoption gap, never
as a confirmed violation.

- Default to under-claiming: if unsure a finding is real, mark it "needs review",
  not "violation".

## Report (audit format) — report-format v3

Every report has four parts in this order: **header**, **glossary**, **findings
table**, **coverage map**. The shape is fixed — same input, same shape, every run
(the audit owes its own output the reproducibility it demands of the code it
reviews).

**1. Header block** — verbatim keys, so a stored report is reproducible:

```
report-format: v3
scope:               <path, diff range, or "repository">
principles-revision: <the "Principles revision" from reference/portable-principles.md>
date:                <YYYY-MM-DD>
commit:              <git SHA of the audited tree, or "working tree (uncommitted)">
```

**2. Principle glossary** — one line per principle *referenced anywhere in this
report*, emitted before the findings, so a reader never meets a bare code
(explain before use). Names come from `reference/portable-principles.md` — do not
paraphrase. Omit principles this report does not cite; on a clean run the glossary
may be empty. Example (include only the rows you cite):

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Every `P#` reference elsewhere in the report renders with its name inline
(`P3 — Confidence + provenance`), never a bare `P3`.

**3. Findings table** — ALWAYS this table, never freeform prose. One row per
finding, columns in this exact order:

| Path | Line | Function | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ----- | ------------- | --------- |
| `src/foo.py` | 42 | `load_scores` | mock value given a `real` source | tag via `derive`, keep `derivedFromMock` | P3 — Confidence + provenance |

- **Path** — repo-relative (never a bare basename; large repos have same-named files).
- **Line** — line or range; `—` if not line-anchored.
- **Function** — enclosing function/symbol, or `—`.
- **Issue** — one-line description.
- **Suggested Fix** — a direction, not a patch.
- **Principle** — the inline-named principle (`P# — <name>`).

**4. Coverage map** — the audit's honest denominator, so a reader can tell what
was actually examined. List every in-scope file (or directory, for a large tree)
marked `read` / `partial` / `not-read`, then state the count and an explicit
no-completeness caveat:

```
coverage: 12/47 files read, 3 partial, 32 not-read (32%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.
```

For a diff-scoped run the denominator is the diff's touched files and coverage is
normally 100% — say so explicitly rather than omitting the map. The map is
REQUIRED on every run: it is the artifact that stops the audit from implying it
found everything when it only sampled.

End with a one-line summary count (e.g. `4 findings: 2 violations, 2 needs-review`).
A clean repo still emits the header, an empty/omitted glossary, an explicit
`No findings.` line in place of table rows, and the coverage map — a clean result
is a valid result, but only over the files the coverage map lists as `read`.

The omission-pass enumeration table (defined in the Method section) is a separate
report artifact with its own columns; when the auditor emits it, its principle
references are inline-named too, exactly like the findings table above.

**Report file — always offer, never auto-write.** Print the full report
(header + glossary + table + summary) to the conversation every run. Then, and
only then, ask whether to save it to `plumb-line-audit.md`; write the file solely
on an explicit yes. Never write it without asking — repeated runs on the same
input MUST produce the same file-write behavior.

## After the report — offer a handoff (read-only; never apply)

The audit reports; it does not fix. After the report is printed and the file
question is settled, OFFER — do not perform — a next step, then stop:

- **Plan the fixes.** Offer to hand the findings to a planning skill (superpowers
  `writing-plans`, or plan mode) to turn them into a fix-plan the builder can work
  through. This produces a plan, not edits — the auditor stays read-only.
- **Close a provenance/enforcement gap.** When the findings include missing
  provenance or lineage, laundered taint, or a layer boundary that nothing
  enforces (P3 — Confidence + provenance, P4 — Quarantined fakery, P8 —
  State-first lineage, P2 — One-way layering), suggest `plumb-line-bootstrap` to
  wire the discipline into the project (host rule file + git hooks). Offer this
  only when such a gap actually appears, not on every run.

Both are suggestions the builder accepts or declines; the auditor applies nothing
itself. Mechanical fixing is a separate, opt-in skill — `plumb-line-remediate`,
which consumes this report's findings table — and this handoff is the bridge to
it, not a substitute. When the builder wants the fixes applied, offer
`plumb-line-remediate` as the third option.
