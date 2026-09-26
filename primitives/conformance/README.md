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
names to your language's binding, run `combine`/`audit`/`validate`, and assert
every field a case carries (including `expectLineageIds`). A JS
implementation can skip the port: pass its module to `runCases()` from
`run-cases.mjs`.
