# ADR-0016: The GitHub Action reads an explicit enforcement manifest and emits one SARIF log

**Status:** Accepted · 2026-09-12

## Context

Review-time enforcement assumed a Claude session. The deterministic half
needs none. A composite Action with SARIF output puts findings in GitHub's
native UI for every contributor (GH #118, ROADMAP #25). Five decisions were
taken 2026-09-11/12 against real alternatives.

## Decision

1. **Run what the consumer carries, from a manifest.** The Action ships no
   layers, globs or defaults (ADR-0004). Rejected: a fixed check set (invents
   answers); a fixed fallback (a hidden default).
2. **One SARIF assembler, fed by machine-readable tool output.** The Python
   CLIs gain `--json`; ESLint uses `--format json`; import-linter is
   text-parsed and labelled `partial`. Rejected: per-tool SARIF emitters
   (four rules catalogues — the #223 drift).
3. **Always upload; fail on findings by default; `fail-on: none` for
   incremental adoption** — the seam the ratchet (#119) will use. Rejected:
   upload-only (inverts the discipline); fail-only (loses the UI).
4. **`.plumb-line/enforcement.json` is the discovery contract**, written by
   bootstrap, validated like every other contracted output. Rejected:
   conventional filenames (the Python output surface has no file; a rename
   silently drops a check); per-path inputs (restates what bootstrap knew).
5. **The Action brings plumb-line's scripts from its pinned ref; the
   consumer's workflow provides ESLint and import-linter.** A missing tool
   is a named failure. Rejected: the Action installs toolchains (versions the
   consumer did not choose); everything from consumer copies (stale rules
   under a new tag).

## Consequences

- `tool-missing` and `errored` fail the job even under `fail-on: none`:
  advisory mode is about findings, never about the Action being unable to
  run.
- The manifest is now a public contract three things read: the Action, the
  ratchet to come, and the skills. Its validator is the gate.
- import-linter's text report is not a versioned contract; the parser is
  pinned to the tested version and a format change degrades to `PL/unparsed`
  warnings. Follow-up filed upstream-facing.
- The bootstrap step is instruction, proven only by the harness — `planned`
  until then.
- This repo's own CI fails outright if the end-to-end SARIF test
  (`test_end_to_end_over_the_planted_fixtures`, the only test proving the
  parsers match what the real tools emit) reports SKIPPED rather than run —
  a skipped proof is a lost proof, so CI installs the fixture toolchain the
  test needs instead of letting it degrade silently.
