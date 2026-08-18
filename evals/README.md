# evals/ — blind validation as a `claude plugin eval` suite (#291)

This directory encodes the release harness's Part 1 (blind validation, see
`docs/release-harness.md` and `examples/AUDIT-EXPECTATIONS.md`) as a
`claude plugin eval` suite, so the non-deterministic layer of the harness can
run repeatably and leave a stored JSON result.

## Cases

One case per fixture variant, mirroring the blind protocol:

| Case | Fixture | PASS means |
| --- | --- | --- |
| `audit-js-broken` | `examples/js-payments-service/broken` | all 3 planted violations confirmed (P2 rates.js, P5 pricing.js, P3 gateway.js) |
| `audit-js-clean` | `examples/js-payments-service/clean` | zero confirmed violations; P7/P9 advisory only |
| `audit-py-broken` | `examples/python-data-pipeline/broken` | all 3 planted violations confirmed (P2 schema.py, P5 aggregate.py, P8 source.py) |
| `audit-py-clean` | `examples/python-data-pipeline/clean` | zero confirmed violations; P7/P9 advisory only |

Each case: `runs: 3` (the harness requires >=2 independent auditors per broken
fixture), an identical plain prompt carrying the declared architecture from
protocol step 3, and a `scaffold.sh` that stages the fixture per protocol step
2 (answer keys deleted, every line naming a violation stripped
case-insensitively, strip verified before dispatch). The scaffold scripts are
plain bash and were tested directly on 2026-08-18; the planted violation lines
survive the strip.

Graders per case: `tool_used` (the audit skill was actually invoked), `regex`
for the v3 report header (format FAIL is scored independently of findings, per
the harness) and for each planted violation's file name, plus an `llm` judge
holding the harness's scoring rule: a planted violation downgraded to advisory
is a FAIL; on clean fixtures any confirmed violation is a FAIL.

## Running

```sh
claude plugin eval                       # all cases
claude plugin eval --case "audit-py-*"   # one fixture
claude plugin eval --json results.json --report report.html
```

## Status and honest caveats

- `claude plugin eval` is early access and org-gated. This suite was authored
  2026-08-18 against the harness format as reported that day and **has not yet
  been executed** (enablement unconfirmed for this account, see #291). Field
  names, `case.yaml` schema details, and scaffold path resolution may need
  adjustment on the first real run.
- Until a green run is recorded in `docs/validation-results.md`, this suite
  supplements the manual protocol in `examples/AUDIT-EXPECTATIONS.md` and does
  not replace it. The manual protocol remains the release gate.
- The eval sandbox runs read-only tools by default, which matches the audit
  skill's read-only contract; no `--allow-tools` should be needed.
