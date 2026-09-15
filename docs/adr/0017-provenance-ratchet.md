# ADR-0017: The provenance ratchet is site-keyed, a mode of the output check, and written only by its CLI

**Status:** Accepted · 2026-09-15

## Context

`require-provenance-output` (ADR-0011) cannot be enabled on a legacy
codebase: every existing untagged output fails at once, so the honest answer
to "how does a 300k-line repo adopt this?" was "it can't" (ROADMAP #26, GH
#119). The proven incremental shape from type-coverage tooling is a ratchet:
pin the current debt, refuse regression. The GitHub Action already reads an
explicit enforcement manifest and emits one SARIF log (ADR-0016); the
ratchet is a new mode of that same manifest and runner rather than a
separate check. Five decisions were taken 2026-09-14/15 against real
alternatives.

## Decision

1. **Site-keyed, not count-only.** A site is `<file>::<symbol>`, the
   enclosing exported/module-level function. Rejected: an integer per
   surface — cheap and rename-proof, but it cannot enforce "no *new*
   untagged outputs": a PR that fixes one and adds one passes. The accepted
   cost is that a rename or move reads as a new site and needs an explicit
   acceptance.
2. **Shrinking is silent; growing needs a reason.** A site leaving the set
   fails nothing and needs no explanation; a site joining it is accepted
   only via `update --because`, appended to the file's history. This is
   Principle 9's explain-the-drift idiom applied asymmetrically, on
   purpose: the ratchet resists one direction.
3. **A mode of the output capability, not a new capability.** One rule id
   (`PL/untagged-output`), one manifest key (`ratchet.file`, on the same
   `.plumb-line/enforcement.json` the Action already reads, ADR-0016);
   pinned sites stay *visible* in SARIF as notes rather than vanishing.
   Rejected: a `js.ratchet` / `python.ratchet` capability with its own
   rule — two checks over the same globs producing overlapping findings.
4. **The runner never writes.** Rejected: auto-pruning from
   `run_checks.py` — in the Action the rewrite is never committed; in the
   pre-commit gate it lands after staging and leaves a dirty tree. Stale
   entries are non-failing notes; `ratchet.py prune` and `update` are the
   only writers.
5. **The lints stay ratchet-unaware.** They gain only the symbol (Python: a
   `symbol` key; JS: a `[site: name]` message suffix, because ESLint's JSON
   carries no per-message data). All ratchet logic lives once, in Python,
   in `adapters/sarif/ratchet.py`. Rejected: a `--ratchet` flag in both
   lints — a third copy of the split, and a JS/Python parity contract to
   maintain for it.

## Consequences

- The manifest validator accepts `ratchet.file` without checking it exists
  (`update` must be able to create it); the runner is what fails on
  absence, with `PL/ratchet-invalid`, regardless of `fail-on`. The
  asymmetry is documented in ACTION.md and both validators' docstrings.
- A ratchet count is a **debt register with a direction, never a grade**
  (ROADMAP #29's guardrail). Nothing here collapses into a score; the
  file lists sites, and the summary reports known/new/stale as three
  numbers, not one.
- An absent `sites` key means "never measured"; an empty list means
  "measured and clean" — the null result is expressible (portable
  principles, the spine).
- The summary format is bumped to **v2** because `findings` changed meaning:
  it no longer counts note-level results, and `notes` and `ratchet` were
  added. A v1 consumer summing `findings` would under-count only when a
  ratchet is configured, but a changed meaning is a changed contract (P7),
  so the version moves rather than the keys quietly shifting under it.
- The JS site marker is a text convention inside a message. The assembler
  turns a marker-less `require-provenance-output` message into
  `PL/unparsed`, so template drift is loud, never a silently site-less
  finding.
- Editor-side ESLint still reports every site as an error. That boundary
  is stated in ACTION.md rather than papered over.
