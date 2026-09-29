# Provenance primitive — JS / Python parity

The provenance/lineage primitive ships in JavaScript (`primitives/js/`) and Python
(`primitives/python/`). The conservative-combination law and the runtime checker
must behave identically in both. This file records the shared case table verified
against both implementations. The two API shapes (for example, JS options
object vs Python keyword arguments, camelCase vs snake_case, and a flat JS
marked object vs Python's `meta` dict) are documented once, in
[`docs/api.md`](../docs/api.md); this file does not repeat them (owner decision
2026-09-28).

Suites: JS `npm ci && npx vitest run`; Python `python3 -m pytest`. Both must
pass in full. The counts are not recorded here, because a count in prose goes
stale (it said 287 / 218 while the suites ran 321 / 233; #525): run them.
(Run JS after `npm ci`: the JS suite includes the fast-check property suite,
which silently fails to import if the dev-dependency is absent.)

**Parity is enforced by data, not prose.** `primitives/conformance/cases.json` is
a single language-neutral case table; `primitives/js/conformance.test.mjs` and
`primitives/python/tests/test_conformance.py` both load it and assert identical
combine/audit/validate/construct results. Adding a row covers both languages at once, and a
divergence fails one suite. The table below is the human-readable summary; the
JSON is the contract.

The table has five case kinds: `combine` (the law), `audit` (logical
consistency), `validate` (structural field-presence — the `validateEnvelope`
/ `validate_envelope` checker added in v0.4.0), `guard` (what the egress
guard passes and refuses, v0.12.0, #120; SPEC §5c), and `construct` (what
`makeMeta` / `make_meta` accepts and refuses, v0.12.0, #443 and #177; both languages
refuse the same JSON-expressible inputs, and the refusal message starts the same; the quoted
value after "got" is each language's JSON rendering and can differ in form for
floats, non-ASCII text and containers). Both checkers report the four
required fields by their canonical camelCase names in both languages, so the
conformance needles match verbatim.

The suite totals differ partly because JS carries a
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

The test-fixture helpers (#123, ADR-0021) add no case kind of their own: the
no-taint check is `guard` with its defaults, so its behaviour is the `guard`
rows'. What they add, the fixture marking and the message prefix `no mock
taint may reach a golden output:`, is pinned by each language's unit tests
(`primitives/js/vitest.test.mjs`, `primitives/python/tests/test_pytest_plugin.py`).

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

## Handed envelopes — resolved 2026-09-29 (#525)

A differential probe fed the same malformed, handed inputs to both
`combine` implementations; 20 of 28 gave different results. All now match,
each pinned by a `combine` row in `cases.json` (the rows marked #525):

- **Step ids for a non-string `confidence` or `source`.** Each language wrote
  the value with its own string conversion (`True` vs `true`, `1.0` vs `1`,
  `1e-07` vs `1e-7`, and containers differently), so the content-addressed
  id differed. Both now use SPEC §4's serialization by type.
- **Python `combine_provenance` was not total.** An input that is not a dict,
  a `lineage` that is not a list, or a lineage step that is not a dict raised
  `AttributeError`; JS combined them. Python now combines them as JS does
  (SPEC §3, "total").
- **Taint of a non-boolean `derivedFromMock`.** JS read `[]` and `{}` as
  tainting (truthy) and Python as clean (falsy), so taint could vanish in
  one language. Both now taint on anything other than `false` or absent,
  so `0` and `""` taint too (SPEC §3).
- **Step shape.** For an input with no `source` or `confidence`, Python
  wrote `null` where JS left the field off (in memory, `undefined`); both now
  write `null`, so every step has both keys. JS spread an array lineage step
  into an object (`{"0": ...}`); both now keep it as an array.

The independent review of the first fix found more, all now resolved and
pinned by rows marked "#525 review": a number beyond double range crashed
Python's id canon; `-0` gave different ids (and Python's `min` over `0.0`
and `-0.0` depended on input order); a lone surrogate crashed Python's
hashing; input ids sorted by UTF-16 unit in JS and by code point in Python;
and the audit's taint-dropped check, `makeMeta`'s coercion and `derive`'s
override each used their language's truthiness rather than the §3 rule. It
also found two regressions in the first fix, fixed before merge: leaving an
absent `source` off a step let the egress guard pass it (the guard now
refuses a step with no `source`), and a Python `Mapping` that is not a `dict`
had its taint cleared (any `Mapping` is now read). A re-run of the reviewer's
143-input probe leaves 18 differences, none in outcome: nine are the audit's
field name in its message (`derivedFromMock` / `derived_from_mock`, as
before), and nine are a `-0` or an out-of-range integer that each language's
JSON parser already reads differently, copied verbatim into the step; the
ids and taint agree.
