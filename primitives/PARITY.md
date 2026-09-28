# Provenance primitive — JS / Python parity

The provenance/lineage primitive ships in JavaScript (`primitives/js/`) and Python
(`primitives/python/`). The conservative-combination law and the runtime checker
must behave identically in both. This file records the shared case table verified
against both implementations. The two API shapes (for example, JS options
object vs Python keyword arguments, camelCase vs snake_case, and a flat JS
marked object vs Python's `meta` dict) are documented once, in
[`docs/api.md`](../docs/api.md); this file does not repeat them (owner decision
2026-09-28).

Suites: JS `npm ci && npx vitest run` → 287/287; Python `python3 -m pytest` → 218/218 (reproduced 2026-09-25).
(Run JS after `npm ci` — the count includes the fast-check property suite, which
silently fails to import if the dev-dependency is absent. Reproduce the number;
never hand-type it.)

**Parity is enforced by data, not prose.** `primitives/conformance/cases.json` is
a single language-neutral case table; `primitives/js/conformance.test.mjs` and
`primitives/python/tests/test_conformance.py` both load it and assert identical
combine/audit/validate/construct results. Adding a row covers both languages at once, and a
divergence fails one suite. The table below is the human-readable summary; the
JSON is the contract.

The table has four case kinds: `combine` (the law), `audit` (logical
consistency), `validate` (structural field-presence — the `validateEnvelope`
/ `validate_envelope` checker added in v0.4.0), and `construct` (what
`makeMeta` / `make_meta` accepts and refuses, v0.12.0, #443 and #177; both languages
refuse the same JSON-expressible inputs, and the refusal message starts the same; the quoted
value after "got" is each language's JSON rendering and can differ in form for
floats, non-ASCII text and containers). Both checkers report the four
required fields by their canonical camelCase names in both languages, so the
conformance needles match verbatim.

The suite totals differ (287 JS vs 218 Python) partly because JS carries a
fast-check **property-test** suite (`property.test.mjs`) with no Python
`hypothesis` mirror yet. Property tests are JS-only and sit *outside* the
conformance contract — parity of the law and checkers is still enforced by the
shared `cases.json`, not by matching suite counts.

`cases.json` is one of three case files in `primitives/conformance/`, each a
separate family with its own kinds. The HTTP adapter's family,
`primitives/conformance/http-cases.json`, has two kinds — `classify` (the
response-to-source/confidence mapping) and `parseAge` (`Age` header
parsing) — and is loaded by `primitives/js/http.test.mjs` and
`primitives/python/tests/test_http.py`.

The baseline library (Principle 9) adds the third file,
`primitives/conformance/baseline-cases.json`, with its own kinds: `attribute`
(findings text pinned verbatim), `canonical` (canonical JSON bytes — compared
as parsed values wherever a float appears), and `validate`. It is loaded by
`primitives/js/baseline.conformance.test.mjs` and
`primitives/python/tests/test_baseline_conformance.py`. The one known
asymmetry is by design, not a defect: an integral float canonicalizes to
`1.0` in Python and `1` in JS. Every `canonical` case asserts parsed
equality; the stronger byte-for-byte claim is made per case by
`expectBytes`, which that one case sets to `false` with its reason recorded
beside it. A second, public-surface naming asymmetry: the
list function is `list` in JS but `list_baselines` in Python, which avoids
shadowing the `list` builtin. The opposite call was made for the `dir`
parameter: Python keeps the name `dir`, shadowing the builtin inside those
functions, so it matches the JS `{ dir }` option and callers' keyword
arguments read the same in both languages. A third, also by design: JS exposes baseline on
the `plumb-line-provenance/baseline` subpath only, so the main entry stays
free of `node:fs` (the `./http` precedent), while Python exports it from the
package — a documented asymmetry of packaging, not of behaviour.

The enforcement hooks outside `primitives/` follow the same rule. Their twins'
CLI behaviour (stdin, environment, exit code, the reason on stderr) is the
fourth case file, `adapters/hook-cases.json`, with one kind per hook
(`branchGuard`, `boundaryGuard`, `preCommitGate`). It is loaded by
`adapters/js/hooks/__tests__/hook-cases.test.mjs` and
`adapters/python/hooks/test_hook_cases.py`, which spawn each hook as a process
(#475). The JS gate's command splitter is also checked word for word against
Python's `shlex.split` (`pre-commit-gate.test.mjs`, #472).
Environment values are read the same way in both twins: one that is not
valid UTF-8, or holds U+FFFD, blocks (#501). Rows set such values as raw
bytes with `envHex`.

**When parity is waived** (owner decision, #505). Parity is required for
behaviour anyone relies on: what a hook allows, what it blocks, and why. It
is not forced where a divergence comes from a runtime's own limits rather
than from a rule, both twins either fail closed or judge correctly, and no
real input reaches it. Copying such a limit into the other twin would make
an accident part of the contract. A waived case is recorded here, with its
waiver on the issue. Waived: a stdin or `PLUMBLINE_CFG` integer of more than
4,300 digits, or JSON nested deeply enough, hits Python's integer-conversion
or recursion limit and blocks in Python, while JS judges it (#505). How deep
depends on the Python version: the exit codes split from about 994 levels on
Python 3.11 (the floor), 9,998 on 3.12 and 3.13, and 87,110 on 3.14 (measured
on macOS by the v0.11.5 dogfood self-audit; JS judged 2,000,000 levels). No
real hook payload or config nests near even the lowest of these.

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

The table is a dated record of that fix, as of 2026-06-28. The first row still
holds. The second has moved on: `{}` now audits to the `version-legacy:`
advisory alone in both languages, because it carries no `provenanceVersion`
(#93, SPEC §5b), and the entry check is on exact container type rather than
`None` (#165; #209 later split its diagnostic). The current behaviour is pinned
by the `cases.json` "empty envelope" row, which requires the advisory, and by
each language's unit test, which requires it to be the only issue
(`audit.test.mjs`, `tests/test_audit.py`), not by this table.
