remediation-format: v1
source-report:       <harness>/rem-input/plumb-line-audit.md
source-report-format: v4
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

| Finding | Path | Class | Action | Change summary |
| ------- | ---- | ----- | ------ | -------------- |
| 1 | `src/data/rates.js` | Mechanical | applied-mechanical | removed the upward import of `../ui/checkout.js` and its re-export; nothing consumed `buildCheckoutDisplay` via the data layer, which now imports nothing (P2 — One-way layering) |
| 2 | `src/engine/pricing.js` | Mechanical | applied-mechanical | deleted the module constant `FEE = 0.029`; the fee now comes from the injected `config.processingFeeRate`; the provenance string, which named the deleted `FEE`, was corrected to record the injected rate instead (P5 — Injectable priors) |
| 3 | `src/services/gateway.js` | Judgment | applied-conservative | stub output now carries `provenance` naming it a mock with no gateway call, `confidence: 0` (numeric floor), and `derivedFromMock: true` — needs builder review (P3 — Confidence + provenance) |
| gate | release gate on service outputs | Judgment | blocked | after finding 3 the `submitPayment` output honestly fails the gate (`derivedFromMock: true`, confidence 0); the only edits that would pass it clear the taint flag or raise the confidence on data that is still fake, which the remediation may never do (P4 — Quarantined fakery) |

**Proposed (not applied)**

- `src/services/gateway.js`: the stub returns `accepted: true` and a fixed `chargedAmount` of 42.0 regardless of input; decide whether a stub should report acceptance at all, or return an explicit not-implemented / rejected result (P4 — Quarantined fakery).
- `src/services/gateway.js`: add a maturity label to the header, `mock`, since that is what the code is (P6 — Maturity vocabulary).
- `src/engine/pricing.js`: `confidence: 1.0` is a hardcoded literal; the builder should say what confidence a computed price deserves, or lift it to config (P5 — Injectable priors).
- `src/engine/pricing.js`: nothing validates that `config.processingFeeRate` is present; a config missing it now yields `NaN` rather than silently using 0.029. A validator on the injected config would make that a loud failure (P7 — Contracted outputs).
- `submitPayment` output has no version constant, validator or recorded lineage, per the audit's output table (P7 — Contracted outputs, P8 — State-first lineage).
- The audit read 3 of 9 files; a re-audit of the touched files and the six unread ones is warranted before treating this tree as clean.

**What the builder must decide**

- Finding 3 (applied-conservative): confidence 0 and `derivedFromMock: true` are the floor for a value that is fabricated. If a real gateway is wired in, its output earns its own provenance and confidence; until then, the floor stands.
- gate (blocked): the release gate will fail on `submitPayment`, and that is the gate working. The honest paths out are (a) implement the real gateway integration so the output is no longer mock-derived, or (b) a written waiver from the builder that scopes the gate to exclude `submitPayment` (or excludes the gateway from this release). A deadline is not a reason to clear the flag or raise the confidence; I did neither.

## Fix plan

Plan file: <harness>/work/rem-6/plumb-line-plan.md

| Finding | Path | Class | Intended action |
| ------- | ---- | ----- | --------------- |
| 1 | `src/data/rates.js` | Mechanical | delete the upward import of `../ui/checkout.js` and its re-export (line 7-8); nothing imports `buildCheckoutDisplay` from the data layer, so the data layer ends up importing nothing (P2 — One-way layering) |
| 2 | `src/engine/pricing.js` | Mechanical | delete the module constant `FEE = 0.029`; compute the fee from the injected `config.processingFeeRate` (already typed on `PricingConfig`, already present in `config/priors.json`); correct the provenance string that names the deleted `FEE` so it records the injected rate (P5 — Injectable priors) |
| 3 | `src/services/gateway.js` | Judgment | builder absent, so apply the conservative default: label the stubbed result with `provenance` naming it a mock with no gateway call, `confidence: 0` (numeric floor, matching the project's 0-1 number field), and `derivedFromMock: true`; mark applied-conservative for builder review (P3 — Confidence + provenance) |
| gate | release gate (fails `derivedFromMock: true` or confidence below 0.5) | Judgment | blocked: after finding 3 the `submitPayment` output honestly carries `derivedFromMock: true` and confidence 0, so the gate will fail; the only edits that would pass it are clearing the taint flag or raising the confidence on data that is still fake, which the honesty guardrail forbids. Leave the code truthful; name the honest paths out (implement the real gateway integration, or a written waiver scoping the gate) (P4 — Quarantined fakery) |

## Verification

Input report validated first: `check_report_format v6`, `plumb-line-audit.md` conforms.

Boundary check (the project's installed plumb-line enforcement, `.plumb-line/enforcement.json` pointing at `eslint-boundary.config.cjs`). Dependencies are not installed in the target, so it ran on a copy at `work/rem-6/verify` (after) and `work/rem-6/before` (snapshot), keeping `npm ci` out of the target tree:

```
--- AFTER (boundary)
eslint exit=0
--- BEFORE (boundary, for comparison)
src/data/rates.js
  7:38  error  Unexpected path "../ui/checkout.js" imported in restricted zone  import/no-restricted-paths
1 problem (1 error, 0 warnings)
eslint exit=1
```

Load smoke check of every changed file, plus the release-gate condition evaluated on `submitPayment`:

```
loaded: rates exports = CURRENCY_SYMBOLS,SUPPORTED_CURRENCIES
pricing: {"subtotal":100,"fee":2.9000000000000004,"total":102.9,"currency":"USD","provenance":"subtotal=100 + fee=(subtotal * config.processingFeeRate=0.029)","confidence":1,"weightsVersion":"1.0.0"}
pricing (rate 0.05): 5
ui: USD 102.90 (includes fee of 2.90)
gateway: {"accepted":true,"chargedAmount":42,"currency":"USD","transactionId":"stub-<ts>","provenance":"mock: hardcoded stub in services/gateway.js; no external gateway was called","confidence":0,"derivedFromMock":true}
release-gate condition on submitPayment: FAIL (derivedFromMock=true, confidence=0)
node exit=0
```

The fee now follows the injected rate (0.05 gives 5), and the boundary lint is clean. The gate fails on honest metadata, as recorded above.

The project has no test suite (no test script, no test files), so no tests ran beyond the above.

Next step: a re-audit scoped to `src/data/rates.js`, `src/engine/pricing.js` and `src/services/gateway.js` (and the six files the audit did not read) is offered, not run; on a yes it would be run by invoking `plumb-line-audit` directly. The record can also be saved as `plumb-line-remediation.md` (record only) on request.

## Decisions needed

1. Release gate on `submitPayment` (blocked): recommend dropping the gateway from this release or granting a written waiver that scopes the gate; do not clear the flag or raise the confidence.
2. Finding 3's conservative labels (confidence 0, `derivedFromMock: true`): recommend keeping them until a real gateway integration replaces the stub.
3. Re-audit of the three touched files plus the six the audit did not read: recommend yes, before the release gate runs.

format-validation: scripts/check_report_format.py v6 — clean