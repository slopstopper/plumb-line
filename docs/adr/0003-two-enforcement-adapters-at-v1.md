# ADR-0003: Two real enforcement adapters at v1 (JS + Python)

**Status:** Accepted · 2026-06-28

## Context

plumb-line's principles are language-neutral, but _enforcement_ is not: a
one-way layering rule is an ESLint config in JS and an import-linter contract in
Python; a test gate is `vitest` here and `pytest` there. The discipline is only
real where a machine checks it, so plumb-line has to ship actual enforcement, not
just advice.

The trap when extracting from a single-language origin (Veska is JS) is to build
an abstraction that secretly assumes that one language and only discovers the leak
when someone tries a second. An abstraction validated against one implementation
is not yet an abstraction.

## Decision

Ship **two real adapters at v1 — JavaScript/TypeScript and Python** — both
implementing a single `adapters/adapter-contract.md`. Every adapter provides the
same four capabilities:

1. **Boundary check** — enforce one-way layering (JS: ESLint
   `import/no-restricted-paths`; Python: `import-linter` contracts).
2. **Test gate** — run the suite (JS: `npx vitest run`; Python: `pytest -q`).
3. **Pre-commit gate** — block a commit if build/test/lint fail.
4. **Branch guard** — block the first code edit on a protected branch.

The guards share a hook I/O convention (JSON on stdin, exit 0 = allow, non-zero +
stderr = block) so the same script works as a git hook and a Claude Code hook.

## Consequences

- Building the second language _before_ shipping forced the contract to be a real
  abstraction rather than a JS-shaped one — the Python adapter is the proof.
- Adding a language later means writing one adapter against the contract and
  touching nothing else; non-shipped languages are labelled **planned** per the
  project's own maturity vocabulary.
- The cost is real parity work: two implementations to keep behaviourally aligned
  for every capability, and that parity burden recurs (see
  [ADR-0005](0005-provenance-primitive-one-law-two-layers.md), where the
  provenance primitive is also dual-language and parity bugs surfaced in review).
- Go, Rust, and other adapters are explicitly out of scope for v1.
