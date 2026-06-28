# Provenance primitive — JS / Python parity

The provenance/lineage primitive ships in JavaScript (`primitives/js/`) and Python
(`primitives/python/`). The conservative-combination law and the runtime checker
must behave identically in both. This file records the shared case table verified
against both implementations.

Suites: JS `npx vitest run` → 34/34; Python `python3 -m pytest` → 25/25.

| Case | derivedFromMock | confidence | source | JS | Python |
|------|-----------------|------------|--------|----|--------|
| `real + mock` (combine) | true | low | derived | ✓ | ✓ |
| `real + semiReal` (combine) | false | medium | derived | ✓ | ✓ |
| `derive` with source override `real` over a mock input | true | — | real (label) | ✓ | ✓ |
| `auditMeta` / `audit_meta` on `derive` output | — | — | — | `[]` | `[]` |

Notes:
- The source-override case proves the escape hatch cannot clear the taint: the
  label becomes `real` but `derivedFromMock` stays `true`, and the checker flags
  that combination as laundering.
- `derive` output is always consistent (the checker returns no issues), because
  `derive` delegates to the single law implementation rather than re-deriving it.

No divergence found between the two languages.
