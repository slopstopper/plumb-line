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
combine/audit/validate/construct/derive/guard results. Adding a row covers both languages at once, and a
divergence fails one suite. The table below is the human-readable summary; the
JSON is the contract.

The table has six case kinds: `combine` (the law), `audit` (logical
consistency), `validate` (structural field-presence — the `validateEnvelope`
/ `validate_envelope` checker added in v0.4.0), `guard` (what the egress
guard passes and refuses, v0.12.0, #120; SPEC §5c), `construct` (what
`makeMeta` / `make_meta` accepts and refuses, v0.12.0, #443 and #177; both languages
refuse the same JSON-expressible inputs, and the refusal message starts the same; the quoted
value after "got" is each language's JSON rendering and can differ in form for
floats, non-ASCII text and containers), and `derive` (what `derive`
writes for an override, v0.12.0, #566). Both checkers report the four
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
Python's `shlex.split` (`pre-commit-gate.test.mjs`, #472). Behaviour that
needs a real git repository is in `adapters/commit-hook-cases.json`: the
branch guard's commit hook (`commitHook`, #464), the gate's branch-aware
mode (`preCommitGate`, #613), and the branch guard's reading of
`core.ignorecase` (`branchGuard`, #615).
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

**Waived (owner decision, 2026-10-03, #594):** handed envelopes' numbers.
A number that the two JSON parsers read differently (`-0`, `1.0`, an
integer beyond double range) is held differently by each twin when
`combine` copies it onto a step. Separately, a guard refusal quotes the
number it refuses in its own language's rendering. That includes `-0.0`
against `0` and `1e-07` against `1e-7`, numbers both parsers read alike.
The taint, the computed ids and the guard's verdict and reason all agree.
Both twins refuse every such input, except a step `id` that is not a
string, which both pass and neither reads. No producer writes a number in
`source`, `confidence`, the taint flag, a lineage step or its `id`. Copying
one parser's reading into the other twin would make an accident part of the
contract.

The same decision waives an object a guard refusal quotes (`{"a": 1}` in
Python against `{"a":1}` in JS). That one fails the rule's first condition,
because the spacing is the default of Python's `json.dumps`, which this repo
chose, not a runtime's limit. It is waived because no behaviour differs, as
ADR-0019's amendment of 2026-10-03 records. The probe's counts and the
residue that is not waived are in "Handed envelopes" below.

**Open divergence, not waived** (v0.12.0 dogfood of #617;
[#625](https://github.com/slopstopper/plumb-line/issues/625)). Where
`core.ignorecase` is true, the hooks compare a branch with the protected
names by folding both (upper, then lower case, #615), and each twin takes its
runtime's own Unicode tables. On a letter whose case mapping is newer than one
runtime's Unicode, the twins disagree: with protected `x꟏` and branch
`x꟎`, Node 24.15 (Unicode 17) blocks a code edit and Python 3.14.4
(Unicode 16) allows it. One twin allows what the other blocks, so this does
not meet the waiver rule above. It is recorded here as open until #625 ships
one reference fold for both twins.

| Case                                                   | derivedFromMock | confidence | source       | JS   | Python |
| ------------------------------------------------------ | --------------- | ---------- | ------------ | ---- | ------ |
| `real + mock` (combine)                                | true            | low        | derived      | ✓    | ✓      |
| `real + semiReal` (combine)                            | false           | medium     | derived      | ✓    | ✓      |
| `derive` with source override `real` over a mock input | true            | —          | real (label) | ✓    | ✓      |
| `auditMeta` / `audit_meta` on `derive` output, no override | —   | —          | —            | `[]` | `[]`   |
| `derive` with source override `real` over a `fallback` input | —     | —          | real (label) | source over-claim | source over-claim |
| numeric `confidenceScore` floors to weakest input      | —               | (0.2)      | derived      | ✓    | ✓      |
| `confidenceScore` omitted on partial coverage          | —               | (omitted)  | derived      | ✓    | ✓      |
| `weakestSource` = weakest source in ancestry           | true            | low        | derived (mock) | ✓  | ✓      |

Notes:

- The source-override case proves the escape hatch cannot clear the taint: the
  label becomes `real` but `derivedFromMock` stays `true`, and the checker flags
  that combination as laundering.
- `derive` output with no `source`, `confidence` or `confidenceScore` override
  is consistent (the checker returns no issues), because `derive` delegates to
  the single law implementation rather than re-deriving it. An override of any
  of those three is a claim the law did not compute, and the checker judges it,
  in both languages. A `source` override over a mock input is laundering (the
  case above), and one cleaner than any ancestor's source is a source
  over-claim (#556): `derive([fallback, real], f, {source: "real"})` audits as
  `source over-claim: source 'real' is cleaner than its ancestry's weakest
  source 'fallback'`. A `confidence` or `confidenceScore` override above the
  weakest input's is an over-claim (`over-claiming: confidence 'high' exceeds
  weakest lineage confidence 'low'`); one at or below it, and a `basis` or
  `adapter` override, pass. This note said "always consistent" until the
  v0.12.0 dogfood audit found it false, and its first fix named only `source`
  (the fix's review).

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

## Handed envelopes (#525) — no difference in outcome found; 36 inputs still differ in form: 30 waived, 4 by design, 2 a gap being fixed (#594, #635)

A handed envelope is one a caller built or parsed itself, not one `makeMeta`
made, so it can carry anything JSON can write. A differential probe fed the
same malformed, handed inputs to both `combine` implementations and found
them giving different results. Every difference in outcome it found now
matches, each pinned by a `combine` row in `cases.json` (the rows marked #525):

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
  one language. #525 first made both taint on anything other than `false`
  or absent. #555 reversed that, because it called an unreadable flag mock:
  now only a boolean `true` taints in both, the constructors refuse a
  non-boolean flag, and combine keeps it on its step for the egress guard
  to refuse as invalid (SPEC §3).
- **Step shape.** For an input with no `source` or `confidence`, Python
  wrote `null` where JS left the field off (in memory, `undefined`); both now
  write `null`, so every step has both keys. JS spread an array lineage step
  into an object (`{"0": ...}`); both now keep it as an array.
- **A `null` `basis` or `adapter`.** JS `makeMeta` stored it as `null`, and
  Python's `make_meta` left it out; both now leave it out, as SPEC §1
  requires of an optional field with no value. A `null` optional override
  on `derive` is no override in both (#566), pinned by the `derive` kind.

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
had its taint cleared (any `Mapping` is now read).

**The counts, run (#594).** This section used to say that 20 of 28 inputs
differed before the fix, and that the review's 143-input probe left 19
differences after #555. Neither probe was committed, so neither count could
be re-run. They are replaced by the counts of the committed probe,
`primitives/conformance/handed_probe.py`. It is a reconstruction from #525's
record with its own corpus, not either earlier probe re-run, and its counts
do not match theirs. It parses each input with each language's own JSON
parser, combines it, audits and guards the result in both twins, and compares
the values each twin holds. A number JSON cannot write (`-0`, an infinity) is
tagged by both, so `JSON.stringify` writing it as `0` or `null` neither hides
a difference nor makes one. `--verbose` lists every difference, `--root DIR`
probes another tree, and it exits 1 on any difference in outcome.
`scripts/test_handed_probe.py` checks this table, the totals and the group
counts below against what it prints. The second column is checked only in a
clone that has the history; CI's shallow checkout skips it.

<!-- handed-probe counts -->
| Class | Inputs, `main` | Inputs, before the fix (`8cef0a2^`) | What differs |
| --- | --- | --- | --- |
| `agree` | 188 | 96 | nothing |
| `outcome` | 0 | 101 | taint, a computed id, a verdict, the record's shape, a throw, or other message text |
| `field-name` | 2 | 11 | a message names the field `derived_from_mock` in Python, `derivedFromMock` in JS |
| `number` | 19 | 9 | one IEEE-754 double, held as different values (`0`/`-0`, `1.0`/`1`, a 401-digit integer/`Infinity`) |
| `quoted-value` | 9 | 3 | a refusal quotes the value in each language's JSON rendering (`-0.0`/`0`, `1e-07`/`1e-7`, `{"a": 1}`/`{"a":1}`) |
| `number+quoted-value` | 6 | 2 | both of those |
| `field-name+number` | 0 | 2 | both of those |
<!-- /handed-probe counts -->

Out of 224 inputs, 36 still differ on `main`. On every one of them, the
taint, the step ids `combine` computes and the guard's verdict agree. A
handed step `id` that is not a string is copied as it is, so on the step-`id`
inputs below the copied value differs. Against the waiver rule above (a
runtime's limit, not a rule; both fail closed or judge correctly; no real
input reaches it), they fall into four groups, decided by the owner on
2026-10-03 (#594).

- **A number on a field that cannot hold one** (15 `number` inputs): a
  `source`, `confidence`, taint flag, lineage step or step `id` of `-0`,
  `1.0` or an integer beyond double range. The two JSON parsers read these
  differently: Python reads `-0` as the integer 0 and `1.0` as a float, and
  keeps the integer exactly, where JS reads `-0`, the number 1 and
  `Infinity`. `combine` copies the value verbatim. This **meets** the rule.
  Both twins refuse all of them as `invalid envelope:`, except the step-`id`
  inputs, which both pass: the guard does not read a step's id, and the
  canon skips an id that is not a string. No producer writes a number in
  these fields. **Waived** (above).
- **A valid score** (4 `number` inputs): a `confidenceScore` of `-0`,
  `-0.0` or `1.0`, or `-0.0` before a `0`. Python holds `0`, `0.0` or `1.0`
  where JS holds `-0`, `0` or `1`: Python's parser reads `-0` as an
  integer, Python keeps a float a float, and its `min` keeps whichever zero
  came first. The value is the same double and both twins pass it. Measured
  against the waiver rule it would fail the third condition, because a
  Python score of `1.0` is ordinary input. But it is not waived. It is
  **by design** (owner decision, 2026-10-03, #594): the value is equal, and
  only its rendering differs. This is as the baseline paragraph above
  records for the baseline library's canonical bytes, and it covers
  `combine`'s scores, the sign of zero included.
- **A quoted value in a refusal** (9 `quoted-value` and 6
  `number+quoted-value` inputs): both twins refuse with the same
  `invalid envelope:` reason and field, but each quotes the value in its own
  rendering. The 6 also hold a number of the first group on the step. The
  guard uses the same quoting as `construct`, whose rendering difference
  ADR-0019 records. The number forms (`-0.0` against `0`, `1.0` against
  `1`, `1e-07` against `1e-7`, 401 digits against `Infinity`) meet the rule
  and are **waived** (above). The 3 object inputs (`{"a": 1}` against
  `{"a":1}`) fail the first condition, because the spacing is the default of
  Python's `json.dumps`, which this repo could change. They are **waived**
  too, because no behaviour differs (above; ADR-0019's amendment of
  2026-10-03).
- **The field's name in a message** (2 `field-name` inputs): Python's
  `taint dropped:` message, and its `laundering:` message (which `combine`'s
  output cannot reach), say `derived_from_mock`. Python's other messages say
  `derivedFromMock`, as JS's do. This **fails** the rule: the name is text
  this repo chose, and every taint-dropped envelope reaches it. It is a gap,
  not waived, and is being fixed in
  [#635](https://github.com/slopstopper/plumb-line/issues/635). The probe's
  `field-name` count, and this table with it, fall to 0 when the fix lands.
