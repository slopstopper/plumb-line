# Plumb-line audit: `./fixture` (js-payments-service-fixture)

**About the skill:** there is no plumb-line audit skill in this session's skill list, so I couldn't call it. I did the audit by hand against the plumb-line principles and the architecture you declared. I read all four source files, `config/priors.json`, the generated boundary rule, and `.plumb-line/enforcement.json`. I also ran the code with sample inputs. Nothing in `./fixture` was changed; the one probe copy is in `$TMPDIR`.

## Declared architecture
- **Layers:** ui → services → engine → data, downward only. Skipping a layer on the way down is allowed.
- **Priors:** come from `config/`.
- **Lineage:** the services result must record what's needed to reproduce it: source identity, record count, field names, and config/version.
- **Metadata:** every output carries provenance and confidence, and passes on the priors version.

## Summary
| Principle | Verdict |
|---|---|
| One-way layering | **Pass by reading the code; not proven by running the check** (the check can't run, see F1) |
| Priors from config, not hard-coded | **Partial.** Nothing is hard-coded, but nothing loads or checks `config/priors.json` |
| Services output records lineage | **Structurally present, but weak** (F3) |
| Provenance, confidence, priors version on outputs | **Present**, but they can be `undefined` or wrong (F2, F4) |
| Fail loudly, never quietly | **Fail.** Bad config or bad input produces NaN or nonsense charges with no error |

## Findings

### F1 — High: the layering check doesn't run
- `eslint-boundary.cjs` has all six upward-import bans. I checked each target/from pair and none is missing. `.plumb-line/enforcement.json` points to the right config file.
- **But the installed ESLint crashes:** `node node_modules/eslint/bin/eslint.js -c eslint-boundary.config.cjs src` fails with `SyntaxError: Unexpected token ')'` in `node_modules/eslint/lib/services/suppressions-service.js:58`. The `.bin/eslint` shim also isn't executable (exit 126).
- Because of that, my probe (engine importing services, data importing engine) couldn't be confirmed as caught.
- `package.json` has no lint script, and I found no CI, so nothing runs the check anyway.
- **What the code actually does today:** all three imports go downward.
  - `ui/checkout.js:8` → engine (a skip, which is allowed)
  - `services/gateway.js:8` → engine
  - `engine/pricing.js:7` → data
- So layering is followed today, but nothing enforces it.
- **Fix:** reinstall `node_modules` cleanly, add `"lint:boundary": "eslint -c eslint-boundary.config.cjs src"`, and run it in CI. Keep a test with a deliberately bad import to prove the rule fires.

### F2 — High: missing or bad priors fail quietly
- `engine/pricing.js:40` reads `config.processingFeeRate` and never checks it.
- Calling `submitPayment(100, "USD", {})` returns `accepted: true`, `chargedAmount: NaN` and `configVersion: undefined`, with no error.
- Nothing in the code actually loads `config/priors.json`. Every caller has to pass config in, and nothing checks it has the right shape.
- **Fix:** add one loader that reads and validates the priors file. It should throw unless `processingFeeRate` is a number in [0, 1) and `version` is a non-empty string. The engine should also refuse config that fails these checks.

### F3 — Medium: the lineage has the declared fields but can't reproduce the charge (`services/gateway.js:44-49`)
- **`source`** is `"engine/pricing.calculateTotal"`. That names the code, not where the inputs came from (caller, order ID, or the priors file path).
- **`fieldNames`** is `Object.keys(priced)`. That lists the engine's *output* fields, including `provenance` and `confidence`, not the input fields the charge was built from.
- **Input values:** the structured response has no `subtotal` or fee rate. The only way to recover them is by parsing the `provenance` text. So the code comment's claim that the lineage holds "the inputs needed to reproduce this charge" isn't true in structured form.
- **`recordCount: 1`** is a hard-coded constant, which is fine for a single payment.
- **Fix:** record the real input source (for example a request or order ID) and the priors file path, list the *input* field names (`subtotal`, `currency`, `processingFeeRate`), and include their values or a hash of them.

### F4 — Medium: the stub claims `accepted: true` (`services/gateway.js:52`)
- The response is honestly labelled (`dataStatus: "simulated"`, `confidence: 0.0`, provenance starting with "stub:").
- But `accepted: true` claims the gateway accepted the payment, which never happened. Any code that only checks `accepted` will treat a fake charge as real, which is exactly how mock data gets passed off as real.
- **Fix:** return `accepted: null` (unknown) or `false` while `dataStatus === "simulated"`, or fail loudly outside test mode.

### F5 — Medium: no input checks, and money math uses unrounded floats
- **Negative amounts:** `submitPayment(-5, "JPY", …)` returns `chargedAmount: -5.145` with no error.
- **Unrounded floats:** `subtotal * feeRate` is never rounded to the currency's smallest unit. `100.1` USD gives `103.0029`.
- **JPY:** it has no minor units, but `ui/checkout.js:33` always uses `toFixed(2)`.
- **Engine confidence:** it hard-codes `confidence: 1.0` (`pricing.js:50`), even when its inputs are NaN.
- **Fix:** reject non-finite or negative amounts, round per currency (keep the decimal places in `data/rates.js`), and use integer minor units.

### F6 — Low: comments contradict the declared architecture (`ui/checkout.js:4-5`)
- The header says "Allowed imports: engine only; never imports services". The declared rule allows ui → services, and that is the path that carries lineage.
- A side effect: the UI works out totals itself through the engine, so what it shows is never the services output. That means no lineage and no `dataStatus`. If the display is meant to show a *charge*, it should use the services result.
- **Fix:** correct the header comment. Decide whether checkout should display the services result, with its lineage.

### F7 — Low: the transaction ID isn't unique or reproducible (`services/gateway.js:37`)
- `stub-${Date.now()}` can repeat for two calls in the same millisecond, and it isn't reproducible. Use `crypto.randomUUID()`, or take an ID passed in by the caller.

### F8 — Info: unused data
- `CURRENCY_SYMBOLS` is only used to derive `SUPPORTED_CURRENCIES`. The UI prints currency codes, not symbols. This is harmless.

## What passes
- No weights are hard-coded. The fee rate is only ever read from config.
- The priors version passes cleanly from engine → services (`weightsVersion` and `lineage.configVersion`) and engine → ui.
- Every layer's output carries provenance and confidence.
- The stub is labelled as simulated with confidence 0, apart from the `accepted` flag in F4.
- The data layer imports nothing.

## Priority order
1. F1: make the layering check actually run.
2. F2: add a priors loader that validates and fails loudly.
3. F4: stop the stub claiming the payment was accepted.
4. F3: make the lineage reproducible.
5. F5: input checks and currency rounding.
6. F6 and F7.
