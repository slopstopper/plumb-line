# Conformance suite

`cases.json` is the **executable definition** of the provenance envelope
([SPEC.md](../SPEC.md)). It is a single, language-neutral case table; both
reference implementations run it (`js/conformance.test.mjs`,
`python/tests/test_conformance.py`), so adding a row covers every language at
once and a divergence fails a suite. Parity is data, not prose.

## Running the report

`report.mjs` runs the cases against the JS reference implementation and prints a
pass/fail report, the envelope schema version, and — when conformant — a badge
snippet. It exits non-zero on any failure, so it works as a CI gate too.

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
[![provenance: plumb-line v1](https://img.shields.io/badge/provenance-plumb--line_v1-3b82f6)](https://github.com/effythealien/plumb-line/blob/main/primitives/SPEC.md)
```

[![provenance: plumb-line v1](https://img.shields.io/badge/provenance-plumb--line_v1-3b82f6)](../SPEC.md)

Generate it (and verify you actually pass before claiming it) with
`node primitives/conformance/report.mjs --badge`.

## Certifying another implementation

A new-language port conforms to **envelope schema version 1** when it produces
the expected result for every case in `cases.json` — see [SPEC §6](../SPEC.md).
Mirror the runner pattern: load `cases.json`, translate the camelCase field
names to your language's binding, run `combine`/`audit`, and assert.
