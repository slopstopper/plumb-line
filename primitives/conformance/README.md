# Conformance suite

`cases.json` is the **executable definition** of the provenance envelope
([SPEC.md](../SPEC.md)). It is a single, language-neutral case table; both
reference implementations run it (`js/conformance.test.mjs`,
`python/tests/test_conformance.py`), so adding a row covers every language at
once and a divergence fails a suite. Parity is data, not prose.

## Running the report

`report.mjs` runs the cases against the JS reference implementation and prints a
pass/fail report, the envelope schema version, the case table the verdict was
earned on (its version, the sha256 of `cases.json`'s bytes, and the case count
per kind; `caseTable` in `--json`), and — when conformant — a badge snippet. A
`cases.json` at a version the runner does not model fails instead of being read
as the one it knows. It exits non-zero on any failure, so it works as a CI gate too.

The case interpreter itself is `run-cases.mjs`, shared with
`scripts/check-bundle-conformance.mjs` (the plugin-bundled copy), so the two
cannot read `cases.json` differently. It reports any case field it does not
interpret as a failure; so do both Python runners. A new field in `cases.json`
therefore fails every runner until each is taught to read it.

The other two case tables, `http-cases.json` and `baseline-cases.json`, are
read by the ordinary test suites (`js/http.test.mjs` and
`python/tests/test_http.py`; `js/baseline.conformance.test.mjs` and
`python/tests/test_baseline_conformance.py`). They have the same three
guards: `table-guards.mjs` and its Python twin
`python/tests/case_table_guards.py` report any case field, case kind or table
version a runner does not interpret, so a new field, case kind or table
version in either table fails until every runner is taught to read it.

```bash
node primitives/conformance/report.mjs          # human report + badge
node primitives/conformance/report.mjs --badge   # badge markdown only
node primitives/conformance/report.mjs --json     # machine-readable result
```

## The handed-envelope probe

`handed_probe.py` (with its JS half, `handed-probe.mjs`) is a differential
probe, not a case table. It generates handed inputs, which are envelopes a
caller built or parsed itself. Each twin parses them with its own JSON
parser, combines, audits and guards them, and the probe counts where the two
differ. [PARITY.md](../PARITY.md) cites its counts, and
`scripts/test_handed_probe.py` checks that PARITY.md states them as printed
(#594). It exits 1 on any difference in outcome.

```bash
python3 primitives/conformance/handed_probe.py --verbose   # counts and each difference
python3 primitives/conformance/handed_probe.py --root DIR  # probe another tree's primitives/
```

Its output, printed and `--json`, names the probed tree's commit (when the
tree is a git checkout) and the Node and Python versions it ran.

## The case-fold sweep

`fold_sweep.py` (with its JS half, `fold-sweep.mjs`) compares the running
Node and Python one code point at a time, as the hooks' case-alias check
reads them (#625, #642). It counts the code points one runtime knows and the
other does not, fold differences, and the composites and combining marks
behind the open divergences [PARITY.md](../PARITY.md) records. PARITY.md
cites its figures as a dated measurement on named runtimes: CI runs one
Node and one Python per job, so it cannot reproduce figures that pair
others. `scripts/test_fold_sweep.py` checks on the pair it runs on that the
folds agree. To measure another pair, run the sweep with that Python and
with that Node first on `PATH`. It exits 1 when a premise of the hooks'
rule fails on the pair.

```bash
python3 primitives/conformance/fold_sweep.py --verbose   # counts and the code points behind them
```

## The badge

A project that enforces provenance with plumb-line (or ships a conformant
implementation of the envelope) can advertise it. The badge links to the spec
version it conforms to:

```markdown
[![provenance: plumb-line v2](https://img.shields.io/badge/provenance-plumb--line_v2-3b82f6)](https://github.com/slopstopper/plumb-line/blob/main/primitives/SPEC.md)
```

[![provenance: plumb-line v2](https://img.shields.io/badge/provenance-plumb--line_v2-3b82f6)](../SPEC.md)

Generate it (and verify you actually pass before claiming it) with
`node primitives/conformance/report.mjs --badge`.

## Certifying another implementation

A new-language port conforms to **envelope schema version 2** when it produces
the expected result for every case in `cases.json` — see [SPEC §7](../SPEC.md).
Mirror the runner pattern: load `cases.json`, translate the camelCase field
names to your language's binding, run `combine`/`audit`/`validate`/`construct`/`derive`/`guard`,
and assert every field a case carries (including `expectLineage`, the whole
lineage, and `expectLineageIds`). A
`construct` case expects your envelope constructor to refuse an off-ladder
`source` or `confidence` with a message containing the pinned text (v0.12.0,
#443), and to refuse a missing `source` rather than default it (v0.12.0,
#177). JSON cannot write "left out", so those rows omit `source` from `input`;
pass only the keys a row carries. A `construct` or `derive` row's `absent`
list names fields the envelope must not have at all (SPEC §1; the rows since
v0.12.0, #566). A `derive` row marks each of its `inputs` with its fields,
then derives with its `override` and any function: the envelope is under
test, not the value. A port certified against schema version 2 before v0.12.0 must re-run:
`construct` and `derive` (#566) are new requirements at the same schema version, signalled by the
table's sha256 and its per-kind counts, not by a version number. So is `guard`
(v0.12.0, #120): a port provides the egress guard of SPEC §5c, and a `guard`
row's `meta` is the envelope of a marked value built the way your `mark`
builds one (a non-object `meta` is passed as the value itself). A JS
implementation can skip the port: pass its module to `runCases()` from
`run-cases.mjs`.
