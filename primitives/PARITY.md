# Provenance primitive — JS / Python parity

The provenance/lineage primitive ships in JavaScript (`primitives/js/`) and Python
(`primitives/python/`). The conservative-combination law and the runtime checker
must behave identically in both. This file records the shared case table verified
against both implementations.

Suites: JS `npm ci && npx vitest run` → 98/98; Python `python3 -m pytest` → 59/59.
(Run JS after `npm ci` — the count includes the fast-check property suite, which
silently fails to import if the dev-dependency is absent. Reproduce the number;
never hand-type it.)

**Parity is enforced by data, not prose.** `primitives/conformance/cases.json` is
a single language-neutral case table; `primitives/js/conformance.test.mjs` and
`primitives/python/tests/test_conformance.py` both load it and assert identical
combine/audit/validate results. Adding a row covers both languages at once, and a
divergence fails one suite. The table below is the human-readable summary; the
JSON is the contract.

The table has three case kinds: `combine` (the law), `audit` (logical
consistency), and `validate` (structural field-presence — the `validateEnvelope`
/ `validate_envelope` checker added in v0.4.0). Both checkers report the four
required fields by their canonical camelCase names in both languages, so the
conformance needles match verbatim.

The suite totals differ (98 JS vs 59 Python) partly because JS carries a
fast-check **property-test** suite (`property.test.mjs`) with no Python
`hypothesis` mirror yet. Property tests are JS-only and sit *outside* the
conformance contract — parity of the law and checkers is still enforced by the
shared `cases.json`, not by matching suite counts.

| Case                                                   | derivedFromMock | confidence | source       | JS   | Python |
| ------------------------------------------------------ | --------------- | ---------- | ------------ | ---- | ------ |
| `real + mock` (combine)                                | true            | low        | derived      | ✓    | ✓      |
| `real + semiReal` (combine)                            | false           | medium     | derived      | ✓    | ✓      |
| `derive` with source override `real` over a mock input | true            | —          | real (label) | ✓    | ✓      |
| `auditMeta` / `audit_meta` on `derive` output          | —               | —          | —            | `[]` | `[]`   |
| numeric `confidenceScore` floors to weakest input      | —               | (0.2)      | derived      | ✓    | ✓      |
| `confidenceScore` omitted on partial coverage          | —               | (omitted)  | derived      | ✓    | ✓      |
| `weakestSource` = weakest source in ancestry           | true            | low        | derived (mock) | ✓  | ✓      |

Notes:

- The source-override case proves the escape hatch cannot clear the taint: the
  label becomes `real` but `derivedFromMock` stays `true`, and the checker flags
  that combination as laundering.
- `derive` output is always consistent (the checker returns no issues), because
  `derive` delegates to the single law implementation rather than re-deriving it.

## Previously-divergent cases — now resolved

The following two cases were identified as divergences between the JS and Python
implementations and have been corrected (fix-wave prov-fixwave, 2026-06-28):

| Case                                                                   | JS behaviour                                                                                     | Python behaviour (before)                                           | Python behaviour (after)                                                                                       |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Invalid / missing top-level `confidence` in `auditMeta` / `audit_meta` | `CONFIDENCE.indexOf(c)` returns `-1`; `-1 > weakest_idx` is always false; no throw; returns list | `CONFIDENCE.index(c)` raised `ValueError`                           | `c = meta.get('confidence'); top_idx = CONFIDENCE.index(c) if c in CONFIDENCE else -1`; no throw; returns list |
| Empty dict `{}` passed to `auditMeta` / `audit_meta`                   | `if (!meta)` is falsy only for `null`/`undefined`; `{}` proceeds and returns `[]`                | `if not meta:` treated `{}` as missing; returned `['missing meta']` | `if meta is None:` only catches `None`; `{}` proceeds and returns `[]`                                         |

Both cases now match. No divergence found between the two languages.
