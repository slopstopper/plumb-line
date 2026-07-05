---
name: plumb-line-remediate
description: Use when applying findings from a plumb-line audit report — the builder has a report (or pasted findings) and wants the fixes made. Opt-in and separate from the audit, which is read-only and never fixes.
---

# Remediate plumb-line audit findings

REQUIRED READING FIRST: `reference/portable-principles.md` (plugin root).
If this file cannot be read, stop immediately and report: "Cannot remediate:
`reference/portable-principles.md` is missing or unreadable. Do not proceed from
memory — the principles file is the source of truth for what a fix must honor."

The audit finds; this skill fixes. The two never blur: remediation runs only on
an explicit invitation, consumes a report the audit produced (any
`report-format: v1`+; v3 is current), and applies nothing the builder has not
seen. If there is no report, offer to run `plumb-line-audit` first, or accept
findings pasted in the findings-table shape (Path / Line / Function / Issue /
Suggested Fix / Principle).

## The contract (what a remediation run IS)

A remediation run produces, in order:

1. a **fix plan** — every finding classified before any edit,
2. **per-finding diffs** — each shown before it is considered done,
3. a **remediation record** — the finding→change table that gives the
   remediation itself the lineage it demands of the code (P8),
4. a **verification step** — the project's own enforcement, run, with output.

Editing a file the builder never sees a diff for, or finishing without the
record, is a failed run — regardless of whether the fixes were correct.

## Step 1 — Classify every finding before touching anything

Read the whole findings table first and classify each row. Print the plan as a
table (Finding / Path / Class / Intended action) before the first edit.

**Mechanical** — the principle determines the fix; no epistemic value must be
invented. Typical: remove an upward import (P2 — One-way layering); replace a
hardcoded constant with the already-existing injected config (P5 — Injectable
priors); add a version constant + validator to an uncontracted output (P7 —
Contracted outputs); record lineage fields that are computable from inputs in
scope (P8 — State-first lineage); relabel maturity to what the code already is
(P6 — Maturity vocabulary); wrap an untagged return in `mark`/`derive` where the
source is unambiguous (P3 — Confidence + provenance).

**Judgment** — the fix requires a claim only the builder can stand behind: which
confidence a value deserves, whether a stub should stay or become a real
integration, which layer a relocated piece of code belongs to, what a changed
baseline's explanation is (P9 — Golden baseline + explain-the-drift). For each
judgment finding, propose a concrete default and ask; apply only on a yes. When
the builder is not present to answer, apply the **conservative default** (below),
mark it `applied-conservative` in the record, and say it needs their review.

**The conservative default: claim nothing the code cannot support.** Where an
epistemic value must be supplied and nobody has answered, take the weakest
honest claim — a fabricated or stubbed value gets the floor (`confidence: 0` /
lowest rung, `source: mock`, `derivedFromMock: true`); an unverifiable origin is
labelled as what it is, not what it is hoped to be. Never pick a "reasonable
middle" (0.5-ish) for a value that is actually fake: an invented moderate
confidence is an invented fact. Two runs on the same input must produce the same
claim — the floor is deterministic; optimism is not.

## Step 2 — Apply one finding at a time, diff shown per finding

Work finding by finding, smallest first if order is free. For each: make the
edit, then show the diff (before/after or unified) labelled with the finding it
resolves, in the conversation, as you go — not a bulk dump at the end. The
builder must be able to stop a bad direction after finding 1, not discover it
after finding N.

**Scope discipline.** Touch only what the finding requires. Adjacent
improvements you notice — a stale comment, a string that could be richer, a
refactor begging to happen — go in the record's **Proposed (not applied)**
section, never into the working tree. One exception, because honesty beats
minimality: if your edit makes an existing statement in the same file false
(a comment or docstring naming a constant you just deleted, a doc line
describing behavior you just changed), correct that statement as part of the
finding's diff — a remediation must not manufacture a lie by omission. Note the
correction in the record.

If a fix for one finding would conflict with the fix for another, stop and
surface the conflict rather than picking silently.

## Step 3 — The honesty guardrail (what a fix may never do)

A remediation may never resolve a finding — or satisfy a gate, a test, a
deadline, or a re-audit — by making the code *less* honest. Concretely, never:

- clear or hand-set a taint flag (`derivedFromMock` and kin) on data that is
  still mock-derived;
- raise a confidence, or swap a source label for a cleaner one, so a check
  passes;
- delete or bypass a null-result / rejection branch so an output always
  succeeds;
- drop a provenance, confidence, or lineage field because its honest value
  is embarrassing;
- update a golden baseline without a recorded explanation of which input moved
  (P9 — the explanation IS the fix; a silent update is the violation).

When the only change that would satisfy a finding, gate, or instruction is one
of these, the finding is **blocked**, not fixable: record it as `blocked` with
the honest paths out (implement the real thing, or obtain an explicit written
waiver that scopes the check), and leave the code truthful. A gate failing on
honest metadata is the gate working; the remediation's job was done when the
metadata became honest. This mirrors bootstrap's rule: if you cannot name a
source-truth layer, that absence is the finding — here, if you cannot fix it
honestly, that impossibility is the finding.

## Step 4 — Verify with the project's own enforcement

After the last fix, run what the project already trusts, and show the output:

- plumb-line adapters if installed (boundary check, `no-provenance-bypass`
  lint, pre-commit gate);
- otherwise the project's own linters/tests that cover the touched files;
- at minimum, an import/load smoke check of every file changed.

Then offer — never auto-run — a re-audit scoped to the touched files, so
find-and-fix stay separate acts with separate records. On a yes, **invoke
`plumb-line-audit` directly** (via the host's skill mechanism) rather than
telling the builder to run it — the baton passes by invocation, not
instruction.

## Step 5 — The remediation record

End every run with the record, then offer — never auto-write — to save it as
`plumb-line-remediation.md` (same always-offer contract as the audit's report
file). The record has a header and a table:

```
remediation-format: v1
source-report:       <path or "pasted findings">
source-report-format: <its report-format version>
principles-revision: <from reference/portable-principles.md>
date:                <YYYY-MM-DD>
commit:              <git SHA before remediation, or "working tree (uncommitted)">
```

| Finding | Path | Class | Action | Change summary |
| ------- | ---- | ----- | ------ | -------------- |

- **Action** is one of: `applied-mechanical`, `applied-judgment` (builder said
  yes), `applied-conservative` (default taken, needs review), `proposed`
  (suggested, not applied), `blocked` (honest fix impossible — reason given),
  `skipped` (builder said no).
- Below the table: the **Proposed (not applied)** list, and one line per
  `blocked`/`applied-conservative` row saying what the builder must decide.
- Principle references render inline-named (`P3 — Confidence + provenance`),
  never bare codes, exactly as in the audit report.

A run where every finding lands as `applied-mechanical` still emits the full
record — the record is the lineage of the remediation, not a summary of its
difficulties.

## Quick reference

| Situation | Action |
| --------- | ------ |
| No audit report exists | Offer `plumb-line-audit` first, or accept pasted findings |
| Fix needs an epistemic value nobody supplied | Conservative floor, `applied-conservative`, flag for review |
| Only a dishonest edit would satisfy the finding/gate | `blocked` + honest paths out; leave code truthful |
| Noticed an improvement no finding asked for | Record under Proposed (not applied) |
| Your edit made a nearby comment/doc false | Correct it within the finding's diff; note in record |
| Two findings' fixes conflict | Stop; surface the conflict |
| All fixes applied | Run project enforcement, show output, offer re-audit |
