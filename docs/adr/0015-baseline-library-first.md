# ADR-0015: Baseline — library-first capture, explained updates, wire-form files, inspection-only CLI

**Status:** Accepted · 2026-09-10

## Context

Principle 9 (golden baseline + explain-the-drift) had no implementation; it
was labelled `not-implemented` (ROADMAP #24, GH #117). Snapshot tools diff
outputs but cannot say which input moved; the envelope's lineage (SPEC §4)
can. Six design decisions were taken 2026-09-10, each against real
alternatives.

## Decision

1. **Capture through the library, inside the project's tests.** `check` /
   `update` take a marked value. Rejected: a CLI capturing envelopes from a
   command's stdout (invents a process protocol); both at once.
2. **Pin the value AND the trust state; drift in either is drift.** Rejected:
   trust state only (cannot make the "value moved, no input changed"
   finding); a hash of the value (cannot show how it changed).
3. **Updates require an explanation, stored with the record as an
   append-only history.** No environment-variable override. Rejected:
   explanation in the commit message; delete-and-rerecord.
4. **One JSON file per baseline name, in the SPEC wire form, language-
   neutral.** Rejected: one shared file (merge conflicts); language-native
   formats (parity becomes a claim).
5. **The CLI is inspection only: `list`, `show`, `validate`.** Only running
   code has the new envelope. Rejected: CLI check/update from an envelope
   file; no CLI.
6. **A missing baseline is a failure whose message names the `update`
   call.** Nothing is created silently. Rejected: auto-record on first run;
   auto-record locally but fail in CI (needs CI detection — a hidden prior).

## Consequences

- P9 is `current` for the library and CLI. Cross-step causality, structural
  diffs inside values, and float tolerance are `not-implemented` and said so.
- The first canonical-JSON writer in the repo exists here; GH #124
  generalises it. Integral floats serialise differently across languages by
  design; comparison is on parsed values.
- Parity extends to a fourth case family (`baseline-cases.json`), with the
  attribution text itself pinned. Tooling parity is kept thin (two ~100-line
  CLIs) rather than mirrored by reflex.
- The library modules are bundled into the plugin; the CLIs are excluded
  with a recorded reason.
