# Dogfooding

plumb-line is held to its own principles. We applied the `plumb-line-audit`
methodology — the same two-pass audit it tells you to run — to plumb-line's own
first-party source, and recorded exactly what it found and what we did about each
finding.

(An auditor that sniffs out code smells should pass its own smell test.)

Date: 2026-06-29 · Version: v0.1.0
Scope audited: `skills/`, `adapters/`, `primitives/`, `reference/`.
Excluded by design: `examples/` (fixtures are intentionally broken — see
[validation results](validation-results.md)) and generated/vendored files
(lockfiles).

## What the audit found

| # | Location | Principle | Finding | Resolution |
| - | -------- | --------- | ------- | ---------- |
| 1 | `adapters/adapter-contract.md:33` | P7 (contract accuracy) | The shared hook I/O contract claimed every guard reads `{ filePath, command }` on stdin. None do: `boundary-guard` reads `{ filePath, importPath }`, `branch-guard` reads `{ filePath }`, and `pre-commit-gate` takes no stdin at all (it reads `PLUMBLINE_TEST_CMD` from the environment). The documented interface did not exist. | **Fixed** — the contract now documents the real per-guard input shapes and carries a contract version. |
| 2 | `primitives/`, `adapters/` outputs | P7 (version anchoring) | No public output shape carried a version constant — not the provenance metadata envelope, not the adapters' `{ allow, reason }` decision. The envelope already has named keys and a validator (`auditMeta` / `audit_meta`), but no version. | **Partial** — declared `PROVENANCE_VERSION` in the primitive (both languages) and versioned the adapter contract. Embedding the version per-output and validating against it is `planned`. |

Two findings, both real, both addressed. The test suites stayed green after the
fixes (primitives 39 JS / 31 Python; adapters 16 JS / 13 Python).

## A note on calibration

The first sweep reported finding #2 as **twelve** separate violations — one per
output-producing function. That is precisely the over-claiming the method guards
against. The audit's calibration rule: a principle adopted *nowhere* in a
codebase is reported **once** as an advisory adoption gap, not N times. Version
anchoring was practiced nowhere, so the honest count is **one** advisory, not
twelve. Collapsing it is the method's under-claiming discipline applied to its
own output — which is the point of recording this at all.

## What was clean

Confirmed by reading context, not keyword matches:

- **P2 (one-way layering)** — no cross-layer imports; `index.mjs` only re-exports
  its siblings.
- **P3 (confidence + provenance) / P4 (quarantined fakery)** — the primitive
  enforces these by construction: taint propagates and cannot be cleared, and
  `auditMeta` flags any laundering. No code hand-builds provenance to bypass the
  law.
- **P5 (injectable priors)** — layers, direction, protected branches, allowlist,
  and the test command are all injected; `STATUS` / `CONFIDENCE` are named
  ordinal lists, not magic priors buried in logic.
- **P9 (drift) / spine (null result)** — no unexplained baselines; the decision
  and checker outputs can all express rejection or an empty result.

## Limits of this audit

This is the methodology applied by a careful reader, not an automated gate. The
automated enforcement plumb-line ships is the lint adapters (ESLint /
import-linter boundaries) and the test suites; this self-audit complements them,
it does not replace them. A finding's absence here means "not found on this
pass," not "provably absent."

## Beyond the fixtures

The auditor has also been run on an unrelated production codebase, where it
surfaced real issues that had passed human review — external corroboration that
the method generalizes beyond plumb-line's own fixtures.

## See also

[validation-results.md](validation-results.md) records the complementary check:
the auditor catching planted violations in the worked fixtures. Validation is the
external test; this is the self-test.
