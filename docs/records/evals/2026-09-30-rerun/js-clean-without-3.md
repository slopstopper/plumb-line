# Plumb-line audit: `./fixture` (js-payments-service-fixture)

**Two limits on this audit:**
1. **The plumb-line audit skill isn't installed in this session.** It isn't among the available skills, and there's nothing under `.claude/`. So I ran the audit by hand, applying the principles as you stated them in the declared architecture (layer direction, priors from config, lineage, provenance, confidence, version propagation, failing loudly). The format and principle numbering may not match the skill's own report exactly.
2. **The ESLint boundary check wasn't run.** `node_modules` is missing, and `npm ci` was blocked because the sandbox denies access to `registry.npmjs.org`. The boundary result below comes from reading the code. The runtime findings come from running `src/services/gateway.js` directly with Node, which works because it has no dependencies.

## Summary

| Area | Verdict |
|---|---|
| Layer direction (ui → services → engine → data) | ✅ Pass |
| Boundary enforcement config | ✅ Correct; ⚠️ not wired into scripts or CI |
| Priors come from `config/` | ✅ Pass (injected); ⚠️ nothing loads or validates them |
| Service-layer lineage | ✅ All four elements present; ⚠️ `fieldNames` lists the wrong fields |
| Provenance / confidence / priors version | ✅ Pass through every layer |
| Fail loudly / no laundering | ❌ **Fail:** a bad config or bad input gives a charge with `accepted: true` |
| Tests | ❌ None |

## 1. Layer direction: pass

| File | Layer | Imports | OK? |
|---|---|---|---|
| `src/ui/checkout.js:8` | ui | engine/pricing | ✅ downward skip, which you allow |
| `src/services/gateway.js:8` | services | engine/pricing | ✅ |
| `src/engine/pricing.js:7` | engine | data/rates | ✅ |
| `src/data/rates.js` | data | none | ✅ |

No upward imports and no cycles.

**Enforcement.** `eslint-boundary.cjs:4-11` lists all six upward pairs for four layers as `no-restricted-paths` zones. `target` is the importing layer and `from` is the forbidden higher layer, so the direction is right. Downward skips are allowed, as you declared. `.plumb-line/enforcement.json` points at the config correctly.
- ⚠️ `package.json` has no `lint` script and there's no CI, so nothing actually runs the check. As shipped, the boundary is only enforced if someone runs it by hand.
- ⚠️ The zone paths are relative to where ESLint runs. It must be run from `fixture/` or the zones won't match.

## 2. Priors from `config/`: pass, with gaps

- `engine/pricing.js:40` reads `processingFeeRate` only from the injected `config`. No fee constant is hardcoded anywhere in `src/`. `config/priors.json` holds `version: "1.0.0"` and `processingFeeRate: 0.029`.
- ⚠️ **No code loads `config/priors.json`.** Every caller passes its own `config` object. The claim that the priors come from `config/` is only made in comments, so a caller can pass any object with any `version` string. A small loader that validates the config, or a single place where the app wires it up, would make that true in code.
- ⚠️ The config is never checked (see §5). A missing `processingFeeRate` is not caught.

## 3. Service-layer lineage: present, with a weakness

`gateway.js:44-49` records the four required elements:
- `source: "engine/pricing.calculateTotal"`
- `recordCount: 1`
- `fieldNames`
- `configVersion`

Tested output:
```json
"lineage": { "source": "engine/pricing.calculateTotal", "recordCount": 1,
  "fieldNames": ["subtotal","fee","total","currency","provenance","confidence","weightsVersion"],
  "configVersion": "1.0.0" }
```

- ⚠️ **`fieldNames` is `Object.keys(priced)`, which lists the engine's output keys, not the inputs.** It even includes metadata fields (`provenance`, `confidence`, `weightsVersion`). You defined lineage as "the inputs needed to reproduce it". The inputs are `subtotal`, `currency` and `config.processingFeeRate` (plus `config.version`). Better: `fieldNames: ["subtotal", "currency", "processingFeeRate"]`.
- ⚠️ **The lineage alone can't reproduce the charge.** It has no input values: no subtotal, no currency, no fee rate. You can only reproduce the charge by parsing the `provenance` string, which also holds `subtotal` and the fee rate. The engine already has typed values, so reproduction shouldn't depend on parsing free text. Consider recording the input values, or the fee rate, in the lineage.
- ✅ `lineage.configVersion` and the top-level `weightsVersion` match.

## 4. Provenance, confidence and priors version: pass

- Engine (`pricing.js:49-51`): provenance shows how the result was derived, `confidence: 1.0` for a deterministic result, and `weightsVersion` taken from `config.version`.
- Services (`gateway.js:56-60`): provenance is marked `stub:` and wraps the engine's provenance, with `confidence: 0.0` and `dataStatus: "simulated"`. The stub is clearly labelled.
- UI (`checkout.js:36-38`): passes provenance, confidence and `weightsVersion` through unchanged.
- ⚠️ Minor: the typedef says "<1.0 when amount is simulated" (`gateway.js:17`), but the code uses 0.0. Also, the amount itself is calculated correctly; what's missing is any gateway confirmation. A confidence of 0 on a correct amount mixes up "is the amount right?" with "was it charged?". Consider a separate `settlementStatus` field, or document what `confidence` measures here.

## 5. Fail loudly / no laundering: fail (the most important finding)

Confirmed by running `submitPayment` directly:

**a. A missing prior quietly gives a non-number charge.**
```
submitPayment(100, "USD", { version: "x" })
→ { accepted: true, chargedAmount: null /* NaN */, confidence: 0,
    provenance: "...processingFeeRate=undefined", lineage.configVersion: "x", ... }
```
`pricing.js:40-42` never checks `processingFeeRate`. `NaN` flows through, and the gateway still says `accepted: true` (JSON turns `NaN` into `null`).

**b. A string input gives a wrong amount.**
```
submitPayment("100", "USD", priors)  →  chargedAmount: "1002.9000000000000004"
```
`subtotal + fee` joins the two as text: `"100" + 2.9`. Nothing checks that `subtotal` is a finite, non-negative number. The UI would also crash on `.toFixed` for a string total (`checkout.js:33`).

**c. The stub reports `accepted: true` unconditionally** (`gateway.js:52`). `dataStatus` is labelled, but any consumer that branches only on `accepted` will treat a simulated charge as real. For a stub, `accepted` should be `false` or `null`, or be removed while `dataStatus === "simulated"`. That way the fake result can't be taken as real by default.

**Fix:** validate at the engine entry point. Throw unless `Number.isFinite(subtotal) && subtotal >= 0`, and unless `config.processingFeeRate` is a finite number in [0, 1) and `config.version` is a non-empty string. This matches how the engine already throws on an unsupported currency (`pricing.js:36-38`).

## 6. Other observations

- **Money is plain floating-point** (`pricing.js:41-42`). `total` is never rounded to the currency's smallest unit; only the display rounds it (`toFixed(2)`). So `chargedAmount` can differ from what the user sees. JPY has no minor unit but still gets 2 decimals. Consider using integer minor units, or rounding each currency's amount in the engine.
- `transactionId` uses `Date.now()` (`gateway.js:37`), so the output can't be reproduced exactly. That's acceptable for a stub, since it's labelled `stub-`.
- **No tests at all.** The findings in §5 are exactly the kind of thing a few engine tests would catch (bad config, non-number subtotal, unsupported currency).

## Prioritised fixes

1. **(High)** Validate `subtotal` and `config` in `calculateTotal`, and throw on bad input (§5a, §5b).
2. **(High)** Stop the stub from reporting `accepted: true` (§5c).
3. **(Medium)** Make `lineage.fieldNames` list the input fields and include the input values or fee rate, so the charge can be reproduced without parsing `provenance` (§3).
4. **(Medium)** Add one loader for `config/priors.json` that validates it (§2).
5. **(Medium)** Add a `lint` script (`eslint -c eslint-boundary.config.cjs src`) and run it in CI. Add engine tests (§1, §6).
6. **(Low)** Handle money in integer minor units per currency, and clarify what `confidence` means in the service layer (§4, §6).

I made no changes to the code.