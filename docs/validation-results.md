# Validation results

An independent check that plumb-line's enforcement catches what it claims to, run against the worked fixtures in `examples/`. Every result below is reproducible from this repository.

Date: 2026-06-28  
Version: v0.1.0  
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


## Static provenance-bypass lint — PB1–PB4

The static lint (SPEC §6) is the review-time complement to the runtime checker.
It is proven against planted violations in both languages, the same way the
boundary and audit checks are.

| Check                                          | JS                | Python            |
| ---------------------------------------------- | ----------------- | ----------------- |
| Rule/checker tests                             | PASS (16/16)      | PASS (21/21)      |
| PB1 laundered meta caught                      | YES               | YES               |
| PB2 manual taint clear caught                  | YES               | YES               |
| PB3 clean source-override on derive caught     | YES               | YES               |
| PB4 re-mark of an unwrapped value caught       | YES               | YES               |
| Quiet on honest usage + dynamic values         | YES               | YES               |
| Quiet on the same shapes imported from elsewhere | YES (not the primitive) | YES (not the primitive) |

Reproduce: JS `cd adapters/js && npm test` (ESLint `RuleTester` exercises the
`no-provenance-bypass` rule); Python `cd adapters/python && python3 -m pytest`
(`provenance_lint.check()` over planted-violation and clean snippets). No misses,
no false positives.

---

## v0.2.0 validation

Date: 2026-06-30 · Version: v0.2.0 · Base commit: cbe8715
Re-run of the enforcement validation against the same `examples/` fixtures on the
v0.2.0 surface (numeric confidence + weakest-source resolution, the conformance
suite, the PB1–PB4 lint adapters). The fixtures themselves are unchanged; this
re-runs the harness to confirm nothing regressed — and one thing had.

### Automated enforcement — deterministic, reproducible

| Check                                  | JS              | Python          |
| -------------------------------------- | --------------- | --------------- |
| Adapter test suite                     | PASS (32/32)    | PASS (34/34)    |
| Example boundary + fixture-integrity   | PASS (10/10, run from repo root) ||
| Cross-language conformance parity gate | `node primitives/conformance/report.mjs` → exit 0 (no divergence) ||

Reproduce: `cd adapters/js && npm test`; `cd adapters/python && python3 -m pytest -q`;
`python3 -m pytest -q examples`; `node primitives/conformance/report.mjs`.

### Blind audit re-run — and a regression it caught

The audit skill is an LLM behavior, scored by the blind protocol in
[`examples/AUDIT-EXPECTATIONS.md`](../examples/AUDIT-EXPECTATIONS.md): one
read-only auditor per fixture variant, answer keys withheld, identical plain
prompt. This time we ran **multiple independent auditors per fixture** rather
than a single pass — more samples surface more of the skill's true behavior,
including its noise.

**A real regression was found and fixed.** On the first pass the auditor **missed
the planted P8 (missing lineage)** in `python-data-pipeline/broken/` — across
**3 of 3** independent runs. Every run caught the P2 and P5 planted violations
but treated the service output's free-text `provenance` string as satisfying the
lineage requirement, never noticing that the structured `lineage` field (source
identity, record count, field names) was entirely absent. P8 is exactly the
omission `AUDIT-EXPECTATIONS.md` calls "the regression this harness exists to
guard," so this scored **FAIL**. Recorded as [issue #31](https://github.com/effythealien/plumb-line/issues/31).

Root cause was a conflation of two distinct fields: a present `provenance`/
`weights_version` answers *where from / which config*, but lineage answers *can I
regenerate this exact output*. The fix:

- **`skills/plumb-line-audit/SKILL.md`** — the omission-pass table now requires a
  **distinct `lineage` column**, separate from `provenance`/`confidence`, and
  states that a present provenance string does not satisfy lineage.
- **`examples/AUDIT-EXPECTATIONS.md`** — the declared-architecture brief now names
  the lineage contract (source, record count, field names, config version) so a
  faithful run supplies the full contract without coaching toward the finding.

**After the fix:** **2 of 2** independent re-runs caught the planted P8 as a
confirmed violation, each with the dedicated lineage column flagging the dropped
field. All three planted violations now caught on every run.

| Fixture (variant)            | Planted set         | Caught (after fix) | Verdict |
| ---------------------------- | ------------------- | ------------------ | ------- |
| js-payments-service/broken   | P2, P5, P3          | 3/3                | PASS    |
| js-payments-service/clean    | none (0 violations) | 0 violations; P7/P9 as advisory gaps, spine as needs-review | PASS |
| python-data-pipeline/broken  | P2, P5, **P8**      | 3/3 (P8 was 0/3 before fix) | PASS (after fix) |
| python-data-pipeline/clean   | none (0 violations) | 0 violations; P7/P9 as advisory gaps | PASS |

### Calibration note — the auditor is noisier than v0.1.0's single pass suggested

Running several blind auditors (not one) shows the skill reliably catches the
**planted set** but also emits additional findings of varying quality:

- **Genuine extras.** On `python-data-pipeline/broken/`, auditors also flagged
  `data/schema.py`'s `validate_and_display` as a P1 violation (derived/display
  logic in the source-truth layer) — a real second facet of the same defect that
  forces the planted P2 upward import.
- **A false positive.** Auditors flagged `services/source.py:42` (`confidence` set
  from `config["stub_confidence"]`) as P3 laundered confidence. This is **noise**:
  the *clean* fixture does the identical thing on purpose (`stub_confidence` is the
  declared injected trust-level for stub data, `clean/.../source.py:57`), and the
  clean-fixture auditor correctly left it alone. Recorded here rather than
  papered over — the honest picture is that an LLM audit catches the planted
  violations but carries a non-zero false-positive rate, so its output is a
  review aid, not a gate.

### Summary

| Check                                  | Result |
| -------------------------------------- | ------ |
| Automated adapters + examples + parity | all green |
| Planted violations caught (all 4 fixtures, post-fix) | YES (incl. the P8 that regressed) |
| Regression found + fixed in this pass  | P8 omission (issue #31) — skill + protocol brief |
| Known residual                         | ~1 false positive per broken-fixture audit (stub-confidence overwrite) |

---

## 0.3.0 release-harness record

Date: 2026-06-30 · Version: v0.3.0 · Base commit: e04ca93
First release run through [`release-harness.md`](release-harness.md). 0.3.0 is a
method-surface release (diff since v0.2.0 touches `skills/`, `primitives/`,
`adapters/`), so the harness applies.

**Deterministic layer (re-run fresh on the 0.3.0 tree):** all green —
primitives **73 JS / 51 Py**, adapters **32 JS / 34 Py**, examples **10/10**,
conformance parity `exit 0`.

**Blind validation layer:** the release-blocking blind audit for this cycle is
the **v0.2.0 validation re-run above** — it found the audit skill missed the
planted P8 (3/3), fixed it, and confirmed **2/2** catch it after. The
`plumb-line-audit` skill and the `examples/` fixtures are byte-identical between
that run and this tree (no method-surface change to either since), so that result
stands as 0.3.0's blind-validation record. **No FAIL outstanding** → not
release-blocking.

**Dogfood self-audit:** covered by the v0.2.0 self-audit ([`dogfood.md`](dogfood.md));
its eight fixes and the audit-skill P8 fix are what 0.3.0 ships. Deferred items
remain tracked (issues #23–#29, #31).

Per the runbook, a fresh standalone blind re-run can be dispatched if a future
release needs a 0.3.0-only record; here it would re-test byte-identical inputs,
so the same-cycle run is cited rather than duplicated.
