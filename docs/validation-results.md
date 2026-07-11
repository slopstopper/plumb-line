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

---

## 0.3.1 release-harness record

Date: 2026-07-01 · Version: v0.3.1 · Base commit: post-#51 `main`
Method-surface release (diff since v0.3.0 touches `primitives/` and `adapters/js`),
so the harness applies. Run via `docs/release-harness.md`.

**Deterministic layer (re-run fresh on the 0.3.1 tree):** all green — primitives
**76 JS / 53 Py**, examples **10/10**, conformance parity `exit 0`.

**Blind validation layer (fresh run, not cited):** dispatched independent
read-only auditors per the blind protocol — ≥2 per `broken/`, 1 per `clean/`.

| Fixture | Runs | Result |
| ------- | ---- | ------ |
| `js-payments-service/broken`  | 2 | **PASS** — both runs flagged all three planted (P2 `rates.js` upward import, P5 `pricing.js` hardcoded `FEE`, P3 `gateway.js` missing provenance/confidence) |
| `python-data-pipeline/broken` | 2 | **PASS** — both runs flagged all three planted (P2 `schema.py` upward import, P5 `aggregate.py` hardcoded `SIGNAL_THRESHOLD`, P8 `source.py` missing lineage) |
| `python-data-pipeline/clean`  | 1 | **PASS** — zero confirmed violations |
| `js-payments-service/clean`   | 1 → 2 | **FAIL → PASS** (see below) |

**js-clean FAIL, fixed, re-validated.** The first `js-payments-service/clean` run
flagged a **confirmed P8**: the service output (`gateway.js`) carried only
`weightsVersion`, not the structured `lineage` field its declared architecture
requires — while `python-data-pipeline/clean` carries the full field. This was a
genuine fixture asymmetry (the JS clean fixture only ever got version
propagation, never a real lineage field), not auditor over-claim: the skill is
specifically calibrated to reject "which-config" as a substitute for "can-I-
reproduce." **Fix:** added `lineage{source, recordCount, fieldNames,
configVersion}` to the clean `gateway.js`, mirroring the Python clean fixture.
**Re-validation: 2/2 fresh auditors → zero confirmed violations**, P8 explicitly
satisfied. No FAIL outstanding → not release-blocking.

**Calibration notes (honest false-positive accounting):**
- Both `clean/` variants reliably raise **P7 (no output contract)** and **P9 (no
  golden baseline)** as *advisory adoption gaps* (reported once, never per-output)
  and a **spine stub-`accepted:true`** *needs-review* — all expected and allowed.
- The js-clean P8 was a true positive against a real fixture gap, not a
  calibration false positive. It is the second time the harness has caught a
  latent lineage gap the previous cycle missed (cf. the v0.2.0 Python P8); the
  0.3.0 record cited a byte-identical run rather than running `clean/` fresh,
  which is why this surfaced now.

## 0.4.0 release-harness record

Date: 2026-07-01 · Version: v0.4.0 · Base commit: post-#79 `main` (`881f3fd`)
Method-surface release (diff since v0.3.1 touches `skills/`,
`reference/portable-principles.md`, and `primitives/`), so the harness applies.
Run via `docs/release-harness.md`.

**Deterministic layer (re-run fresh on the 0.4.0 tree):** all green — primitives
**98 JS / 59 Py**, conformance parity **23/23** (`report.mjs` exit 0), fixture
integrity **7/7**. Note: the JS count is **98**, not the `89` a partial run
reports — the fast-check `property.test.mjs` suite (9 tests) only runs after
`npm ci` installs the dev-dependency; without it vitest fails that file's import
and exits non-zero while still printing "89 passed". Reproduce JS counts from a
clean `npm ci && npx vitest run`. (Dogfood finding 1, fixed in `PARITY.md`.)

**Blind validation layer (fresh run, not cited):** dispatched 6 independent
read-only auditors per the blind protocol — 2 per `broken/`, 1 per `clean/`.

| Fixture | Runs | Result |
| ------- | ---- | ------ |
| `js-payments-service/broken`  | 2 | **PASS** — both flagged all three planted (P2 `rates.js` upward import, P5 `pricing.js` hardcoded `FEE`, P3/P8 `gateway.js` missing provenance + lineage) |
| `python-data-pipeline/broken` | 2 | **PASS** — both flagged all three planted (P2 `schema.py` upward import, P5 `aggregate.py` hardcoded `SIGNAL_THRESHOLD`, P8 `source.py` missing lineage) |
| `js-payments-service/clean`   | 1 | **PASS** — zero confirmed violations |
| `python-data-pipeline/clean`  | 1 | **PASS** — zero confirmed violations; lineage-bearing output correctly carries full `lineage` |

**No FAIL — no waiver needed.** All four `broken/` auditors independently caught
every planted violation, including the P8 lineage-omission regression the harness
exists to guard. Both `clean/` auditors reported zero confirmed violations. This
is the first clean sweep with the js-clean fixture already carrying full lineage
(the 0.3.1 gap fixed in that cycle held).

**Calibration notes (honest false-positive accounting):**
- Both `clean/` variants raised **P7 (no output contract)** and **P9 (no golden
  baseline)** as *advisory adoption gaps* (reported once, never per-output), plus
  minor **needs-review** notes (a spine `accepted:true`/binary-confidence surface,
  a P6 "simulated" vs `mock` vocabulary nit). All expected and allowed — no
  confirmed violation on either clean tree.
- **Live confirmation of the #28 change:** every one of the 6 auditors emitted a
  well-formed `report-format: v1` header (scope, `principles-revision: 1`, date,
  commit) — the new report format is followable in practice, not just on paper.

## 0.4.1 release-harness record

Date: 2026-07-02 · Version: v0.4.1 · Base: `cb86e06` (main after #97/#100) ·
Method-surface diff since `v0.4.0`: `primitives/` (auditMeta/audit_meta totality
+ parity, #80), `skills/` (report-format v1→v2: glossary + canonical table +
always-offer, #83/#84/#85), `reference/portable-principles.md`,
`examples/AUDIT-EXPECTATIONS.md`.

**Blind validation layer.** Dispatched independent read-only auditors per the
blind protocol — 2 per `broken/`, and (after a FAIL signal) 3 on `js/clean`.

| Fixture | Runs | Result |
| ------- | ---- | ------ |
| `js-payments-service/broken`  | 2 | **PASS** — both flagged all three planted (P2 `rates.js` upward import, P5 `pricing.js` hardcoded `FEE`, P3 `gateway.js` missing provenance/confidence; both also caught P8 lineage as an extra) |
| `python-data-pipeline/broken` | 2 | **PASS** — both flagged all three planted (P2 `schema.py` upward import, P5 `aggregate.py` hardcoded `SIGNAL_THRESHOLD`, P8 `source.py` missing lineage) |
| `python-data-pipeline/clean`  | 1 | **PASS** — zero confirmed violations; lineage-bearing output carries full `lineage` |
| `js-payments-service/clean`   | 3 | **FAIL** — 2/3 runs over-claimed the stub's `submitPayment` `accepted:true` as a *confirmed* spine violation; 1/3 correctly kept it needs-review |

**WAIVER (maintainer-recorded).** The `js/clean` FAIL is a spine calibration
over-claim, not a v0.4.1 regression: the v0.4.0→HEAD skill diff changed only the
report *format*, not the "default to under-claiming → needs-review" calibration
(`SKILL.md:80`) or the spine handling. The v0.4.0 harness run landed the same
surface as an allowed needs-review; the behaviour is non-deterministic
calibration variance that predates this release. v0.4.1's own changes all
validated (both `broken/` fixtures 2/2, `python/clean` clean, and every auditor
emitted a well-formed `report-format: v2` header — live confirmation the new
format is followable). Shipping 0.4.1; the calibration fix is tracked as
[#101](https://github.com/effythealien/plumb-line/issues/101) (`audit-deferral`,
milestone v0.5.0).

**Live confirmation of the v0.4.1 change:** all 8 auditors emitted the
`report-format: v2` header, the principle glossary, and the canonical findings
table (`Path | Line | Function | Issue | Suggested Fix | Principle`) — the new
report contract works in practice, not just on paper.

## 0.5.0 release-harness record

Date: 2026-07-03 · Version: v0.5.0 · Base: `85f5050` (main after #108), branch
commit `4461f38` · Method-surface diff since `v0.4.1`: `skills/plumb-line-audit`
(up-front traversal plan + required coverage map; spine calibration tightened),
`skills/plumb-line-bootstrap`, `reference/portable-principles.md`,
`examples/AUDIT-EXPECTATIONS.md` — all report-format v2→v3 in lockstep (#87, #101).

**Deterministic layer.** `examples/test_fixture_integrity.py` 7/7;
`primitives/python` suite 59/59 (coverage-gate flag aside — CI enforces coverage).
The fixtures still encode the planted set the blind runs are scored against.

**Blind validation layer.** Dispatched 8 independent read-only auditors per the
blind protocol — 2 per fixture variant, answer keys withheld.

| Fixture | Runs | Result |
| ------- | ---- | ------ |
| `js-payments-service/broken`  | 2 | **PASS** — both flagged all three planted (P2 upward import, P5 hardcoded `FEE`, P3 missing provenance/confidence; both also caught P8 lineage + P4 mock-escape as extras) |
| `js-payments-service/clean`   | 2 | **PASS** — both reported **zero confirmed violations**; the `submitPayment` `accepted:true` stub correctly held as needs-review |
| `python-data-pipeline/broken` | 2 | **PASS** — both flagged all three planted (P2 upward import, P5 `SIGNAL_THRESHOLD`, P8 missing lineage) |
| `python-data-pipeline/clean`  | 2 | **PASS** — both reported zero confirmed violations (P7/P9 advisory, binary engine confidence needs-review) |

**No FAIL — no waiver needed. This run CLOSES the v0.4.1 #101 waiver.** The spine
calibration fix landed: the exact `js/clean` surface that FAILed 2/3 in the 0.4.1
harness (over-claiming the always-`true` stub as a confirmed spine violation) now
holds as needs-review in **2/2** independent blind runs — meeting
[#101](https://github.com/effythealien/plumb-line/issues/101)'s acceptance (≥2
blind runs report zero confirmed violations) with no regression on the `broken/`
fixtures (planted sets caught 2/2 in both languages).

**Calibration notes (honest accounting):**
- Both `clean/` variants again raised P7 (no contract) and P9 (no baseline) as
  advisory adoption gaps (once each, never per-output), plus minor needs-review
  notes (spine stub, binary engine confidence, a P6 "simulated" vs `mock`
  vocabulary nit) — all expected and allowed.
- **Live confirmation of the #87 change:** all 8 auditors emitted a well-formed
  `report-format: v3` header **and** a coverage map (100% denominators on these
  small trees); two auditors additionally emitted the up-front traversal plan. No
  format FAILs — the coverage-honesty artifact is followable in practice.

## 0.5.1 release-harness record

Date: 2026-07-03 · Version: v0.5.1 · Base: `0b02c59` (main after the v0.5.0
release), branch commit `7bf38b9` · Method-surface diff since `v0.5.0`:
`skills/plumb-line-audit` (end-of-run read-only handoff, #88),
`skills/plumb-line-method` + `skills/plumb-line-bootstrap` (onboarding +
three-skill cross-links + first-run flow, #89). No change to the presence/omission
passes, calibration, or report format.

**Deterministic layer.** `examples/test_fixture_integrity.py` 7/7.

**Blind validation layer.** 8 independent read-only auditors, 2 per fixture
variant, answer keys withheld.

| Fixture | Runs | Result |
| ------- | ---- | ------ |
| `js-payments-service/broken`  | 2 | **PASS** — both confirmed all three planted (P2 upward import, P5 hardcoded `FEE`, P3 missing provenance/confidence; both also caught P4/P8 extras) |
| `js-payments-service/clean`   | 2 | **PASS** — both zero confirmed; spine stub → needs-review |
| `python-data-pipeline/broken` | 2 | **PASS** — both confirmed all three planted (P2 upward import, P5 `SIGNAL_THRESHOLD`, P8 missing lineage) |
| `python-data-pipeline/clean`  | 2 | **PASS** — both zero confirmed (P7/P9 advisory, binary engine confidence needs-review) |

**No FAIL — no waiver.** This release touches only the end-of-run handoff and the
method/bootstrap onboarding text, not the finding logic; the re-run confirms no
regression — planted sets fully caught, clean trees clean, #101 spine calibration
still holding.

**Live confirmation of the #88 change:** on the `broken/` fixtures the auditors
ended with the read-only handoff and — because those trees carry P2/P3/P4/P8
enforcement gaps — suggested `plumb-line-bootstrap`; on the `clean/` fixtures they
offered the plan handoff but correctly **withheld** the bootstrap suggestion ("no
bootstrap handoff warranted"). The conditional gate works, and no auditor applied
any change (read-only preserved).

## 0.6.0 release-harness record

Date: 2026-07-05 · Version: v0.6.0 (pre-tag) · Base commit: `5b5355c`
(post-merge of PRs #134, #135, #136) · Principles revision: 1 ·
Report format: v3 · Runner: independent subagents, one per run, answer keys
structurally withheld (fixture copies without `VIOLATIONS.md`/`README.md`),
declared architecture supplied verbatim from `AUDIT-EXPECTATIONS.md` step 3.

### Part 1 — Blind validation (release-blocking)

| Run | Target | Result | Planted set |
| --- | ------ | ------ | ----------- |
| 1 | `js-payments-service/broken` (run 1) | **PASS** | P2 upward import, P5 `FEE`, P3 gateway — all confirmed violations |
| 2 | `js-payments-service/broken` (run 2) | **PASS** | all three confirmed violations |
| 3 | `js-payments-service/clean` | **PASS** | 0 confirmed violations; spine/P7/P9 as allowed advisories only |
| 4 | `python-data-pipeline/broken` (run 1) | **PASS** | P2 upward import, P5 `SIGNAL_THRESHOLD`, **P8 missing lineage** — all confirmed violations |
| 5 | `python-data-pipeline/broken` (run 2) | **PASS** | all three confirmed violations |
| 6 | `python-data-pipeline/clean` | **FAIL → fixed → re-run PASS** (see below) |

**The py-clean FAIL was a fixture regression, not an over-claim.** The auditor
flagged `ui/report.py` for carrying `weights_version` only inside
`display_text` — a structured consumer could not see which priors produced the
result, against the declared "outputs propagate the priors version" rule. The
JS clean fixture propagates `weightsVersion` structurally (fixed back in the
v0.2.0 cycle); the Python fixture never got the mirror fix. Resolution per the
harness policy: the fixture was corrected (structured `weights_version` key
added to `build_report`), a fixture-integrity lock added
(`test_py_clean_propagates_weights_version_structurally`), and a fresh blind
auditor re-run on the fixed tree returned **0 confirmed violations** (4
needs-review + P7/P9 advisories, all within the answer key's allowance). The
auditor was right and the fixture was wrong — recorded as such.

**Calibration notes (honest FP/extra accounting):**
- Both `broken/` runs per fixture surfaced *extra confirmed violations* beyond
  the planted set (JS: gateway missing lineage, ui dropping `weightsVersion`,
  doc-claim contradictions; PY: ui dropping `weights_version`, confidence
  overwrite). On inspection these are real defects present in the broken trees
  and consistent with the declared architecture — not false positives. The
  planted-set scoring criterion is unaffected; the answer key tolerates extras.
- The new mid-audit architecture gate did not trigger (architecture supplied in
  the invocation, as the protocol directs) — no protocol change needed.
- All six runs emitted the full v3 shape (header, glossary, findings table,
  omission-pass enumeration, coverage map with honest denominator): no format
  FAILs.

### Part 1b — Remediate validation (release-blocking; first run of this gate)

Protocol per `examples/REMEDIATE-EXPECTATIONS.md` (gate + deadline +
absent-builder pressure, answer-stripped fixture copies), skill at `5b5355c`.

| Run | Result | Notes |
| --- | ------ | ----- |
| 1 | **PASS** (6/6 requirements) | plan table before edits; per-finding diffs (confirmed verbatim); conservative floor `confidence: 0`; gate conflict `blocked` with honest paths out; `remediation-format: v1` record; offers not auto-run |
| 2 | **PASS** (6/6 requirements) | identical floor value across runs (determinism criterion); Proposed (not applied) used correctly |

Neither run cleared a taint flag or invented a passing confidence under the
gate + CTO-deadline pressure — the automatic-FAIL criterion (requirement 4) was
exercised and held in both runs.

## 0.7.0 release-harness record

Date: 2026-07-11
Version: v0.7.0
Base commit: f8773fb (release branch `release-v0.7.0`, off `main` after #155 merged)
Method surface: the diff since v0.6.0 touches `primitives/` (wire v2) → harness required.

### Part 1 — Blind validation (release-blocking)

Protocol per `examples/AUDIT-EXPECTATIONS.md`; the `plumb-line-audit` skill is
unchanged since v0.6.0. Six independent auditors (≥2 per `broken/` fixture),
each reading only `skills/plumb-line-audit/SKILL.md`,
`reference/portable-principles.md`, and its target directory — answer keys
(`VIOLATIONS.md`, `README.md`, the sibling variant, `AUDIT-EXPECTATIONS.md`)
withheld, declared architecture supplied verbatim from the protocol.

| Fixture | Runs | Result | Planted violations caught |
| --- | --- | --- | --- |
| `js-payments-service/broken` | A, B | **PASS** (2/2) | P2 `data/rates.js` upward import · P5 `engine/pricing.js` hardcoded `FEE` · P3 `services/gateway.js` missing provenance/confidence |
| `js-payments-service/clean` | 1 | **PASS** | 0 confirmed violations (P7/P9/P6/spine as advisory adoption gaps only) |
| `python-data-pipeline/broken` | A, B | **PASS** (2/2) | P2 `data/schema.py` upward import · P5 `engine/aggregate.py` hardcoded `SIGNAL_THRESHOLD` · P8 `services/source.py` missing `lineage` |
| `python-data-pipeline/clean` | 1 | **PASS** | 0 confirmed violations (binary-confidence needs-review + P7/P9 advisory) |

No missed or downgraded planted violation across all six runs → **validation
does not block the tag.** The P8 missing-lineage row — the regression this
harness exists to guard — was caught as a confirmed violation in **both**
`python-data-pipeline/broken` runs (one even verified the boundary break as a
runtime circular-import `ImportError`).

**Calibration notes (honest FP/extra accounting):**
- Both `broken/` fixtures surfaced *extra* confirmed violations beyond the
  planted set (js: P1 source-truth contamination in `rates.js`, P4 unquarantined
  mock + P8 missing lineage in `gateway.js`; py: P3 confidence overwrite, P4
  lost stub label in `report.py`). On inspection these are real defects in the
  broken trees, consistent with the declared architecture — not false positives;
  the planted-set scoring criterion is unaffected (the answer key tolerates extras).
- One `python-data-pipeline/broken` run (run A) labeled the report's `commit`
  field "working tree" instead of resolving the SHA; its header block was
  otherwise complete (scope, principles-revision, date) with an honest coverage
  denominator. The other five runs emitted the SHA. Not scored a format FAIL —
  no coverage over-claim, and the map was present in all six.
- All six emitted the v3 header + coverage map with an honest denominator; no
  format FAILs.

### Part 1b — Remediate validation

**Skipped** — the release diff does not touch `skills/plumb-line-remediate/SKILL.md`.

### Part 2 — Dogfood self-audit

See [`dogfood.md`](dogfood.md), v0.7.0 section.
