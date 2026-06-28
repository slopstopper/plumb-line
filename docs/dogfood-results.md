# Dogfood results — plumb-line generalization check

Date: 2026-06-28  
Branch: feature/initial-build  
Fixtures: `examples/js-payments-service/` and `examples/python-data-pipeline/`

---

## JavaScript adapter

**Adapter test suite:** PASS (2 test files, 9 tests, 0 failures)

**Boundary guard — planted P2 break:**

- Input: `filePath=src/data/rates.js`, `importPath=../ui/checkout.js`, `direction=downward`
- Output: `{ allow: false, reason: 'boundary break: data must not import ui (downward)' }`, exit 0
- Result: CAUGHT

**Audit of `examples/js-payments-service/broken/` (independent findings before reading answer key):**

| File                      | Line  | Principle | Finding                                                                                                                                                                                     |
| ------------------------- | ----- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/data/rates.js`       | 8     | P2        | Boundary leak: data layer imports `buildCheckoutDisplay` from `../ui/checkout.js`. Upward import against declared direction.                                                                |
| `src/engine/pricing.js`   | 10    | P5        | Hardcoded prior: `const FEE = 0.029` used directly in calculation instead of `config.processingFeeRate`, which the typedef and comments declare as the correct source.                      |
| `src/services/gateway.js` | 17–18 | P3        | Laundered data: `MOCK_CHARGED_AMOUNT = 42.0` returned as `chargedAmount` with no `provenance`, `confidence`, or `dataStatus` fields. Caller cannot distinguish stub value from live amount. |

3 findings total.

Comparison to `VIOLATIONS.md` answer key: **exact match** — all 3 planted violations found, no false positives.

**Audit of `examples/js-payments-service/clean/`:** No findings. Clean fixture is clean.

---

## Python adapter

**Adapter test suite:** PASS (9 tests, 0 failures)

**Boundary guard — planted P2 break:**

- Input: `file_path=src/data/schema.py`, `import_path=src/ui/report.py`, `direction=downward`
- Output: `{'allow': False, 'reason': 'boundary break: data must not import ui (downward)'}`, exit 0
- Result: CAUGHT

**Audit of `examples/python-data-pipeline/broken/` (independent findings before reading answer key):**

| File                      | Line           | Principle | Finding                                                                                                                                                                                                                           |
| ------------------------- | -------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/data/schema.py`      | 7              | P2        | Boundary leak: data layer imports `build_report` from `src.ui.report`. Upward import against declared direction.                                                                                                                  |
| `src/engine/aggregate.py` | 9              | P5        | Hardcoded prior: module-level `SIGNAL_THRESHOLD = 0.65` used directly (`threshold = SIGNAL_THRESHOLD`) instead of `config["signal_threshold"]`, which exists in the config dict and is used in the clean version.                 |
| `src/services/source.py`  | (return value) | P8        | Missing lineage: `load_and_aggregate` returns a computed result with no `lineage` field. The source used, record count, field names, and config version are not recorded — the output cannot be reproduced from what is returned. |

3 findings total.

Comparison to `VIOLATIONS.md` answer key: **exact match** — all 3 planted violations found, no false positives.

**Audit of `examples/python-data-pipeline/clean/`:** No findings. Clean fixture is clean.

---

## Summary

| Check                                | JS              | Python          |
| ------------------------------------ | --------------- | --------------- |
| Adapter tests                        | PASS (9/9)      | PASS (9/9)      |
| Boundary guard caught P2             | YES             | YES             |
| Audit found exact planted violations | YES (3/3, 0 FP) | YES (3/3, 0 FP) |
| Audit quiet on clean fixture         | YES             | YES             |

No misses. No false positives. No follow-ups required.


## Shipped boundary enforcement — proven separately

The boundary checks above exercise the adapters' `decide()` reference
implementation. The enforcement that bootstrap actually installs into a target
repo is the lint config the adapters template out — ESLint
`import/no-restricted-paths` (JS) and `import-linter` layers (Python). Those
shipped mechanisms are proven directly against these same fixtures by
integration tests that run the real linters:

- JS: `adapters/js/hooks/__tests__/boundary-lint.integration.test.mjs` — real
  ESLint flags the `broken/` upward import and passes `clean/`.
- Python: `examples/python-data-pipeline/test_boundary_lint.py` — real
  import-linter fails the `broken/` layers contract and passes `clean/`.

Declared layer order for both fixtures: `ui → services → engine → data`
(the service layer uses the pure engine, which uses static data; `data` is the
bottom layer, so the planted `data → ui` import is an upward violation).
