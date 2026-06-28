# ADR-0007: Branch-guard allowlist hardening

**Status:** Accepted · 2026-06-28

## Context

Each adapter ships a **branch guard** (see
[ADR-0003](0003-two-enforcement-adapters-at-v1.md)) that blocks the first code
edit on a protected branch while permitting edits to an allowlist of paths
(documentation, typically). The guard is a security boundary: it decides whether
a write is permitted. An allowlist that is too loose silently defeats the guard.

A security review of the v0.1 guards found the allowlist matching was unsafe in
both the JS and Python adapters. Three bypass classes existed:

1. **Path traversal** — a path containing `..` could escape the allowlisted
   directory while still appearing to match it.
2. **Prefix overmatch** — naive `startsWith`-style matching let an allowlisted
   prefix (`docs`) also match unintended siblings (`docs-secret/`, `docs.js`),
   because it matched characters, not path segments.
3. **Empty-entry match-all** — an empty allowlist entry matched _every_ path,
   turning the guard off entirely.

Because the same logic was mirrored across two languages, each flaw existed
twice.

## Decision

Harden allowlist matching in both adapters, fixed with TDD (failing test per
bypass class first, then the fix), in JS and Python in parity:

- **normalize and resolve** candidate paths before comparison, and **reject paths
  containing `..`** so traversal cannot escape an allowlisted root;
- match on **path-segment boundaries**, not raw string prefixes, so `docs` does
  not match `docs-secret`;
- **reject empty allowlist entries** rather than treating them as wildcards.

## Consequences

- The branch guard is a real boundary again: the three bypass classes are closed
  and covered by regression tests in both languages.
- This reinforces the parity cost noted in ADR-0003 — a security fix is two fixes,
  and the tests that prove it are two suites. The upside is that the shared
  adapter contract made it obvious the same flaw applied to both.
- Allowlist entries are now stricter: a contributor adding a doc path must give a
  clean, traversal-free, non-empty, segment-aligned path. This is intended — the
  guard should be conservative about what it lets through on a protected branch.
