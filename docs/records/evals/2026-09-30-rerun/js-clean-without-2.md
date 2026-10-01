# Plumb-line audit: `./fixture` (js-payments-service-fixture)

**About this audit:** I couldn't find a plumb-line audit skill. It isn't in this session's skill list, and neither `~/.claude/skills` nor the project has one. So I did this audit by hand against the principles and architecture you gave me, reading every file in the fixture. I also couldn't run the generated ESLint boundary check: `node_modules` isn't installed, and the sandbox blocked `registry.npmjs.org` (403). The layering results below come from reading all the import statements by hand, not from the linter.

## Scope

| Layer | File | Imports |
|---|---|---|
| ui | `src/ui/checkout.js` | `../engine/pricing.js` |
| services | `src/services/gateway.js` | `../engine/pricing.js` |
| engine | `src/engine/pricing.js` | `../data/rates.js` |
| data | `src/data/rates.js` | none |
| config | `config/priors.json` | — |
| enforcement | `eslint-boundary.cjs`, `eslint-boundary.config.cjs`, `.plumb-line/enforcement.json` | — |

## Summary

| Principle | Verdict |
|---|---|
| One-way layering (ui → services → engine → data) | **Pass** |
| Layering is enforced mechanically | **Pass (not run here)** |
| Priors come from `config/` | **Partial.** Nothing in the code loads `config/`. |
| Services output carries lineage | **Pass, with weaknesses** |
| Outputs carry provenance and confidence | **Pass, with one honesty concern** |
| Priors version is passed along | **Pass** |

No blocking violations. There are 2 medium findings and 4 low ones.

---

## Principle 2: One-way layering

**Pass.** All three imports go downward:
- ui → engine (`checkout.js:8`). This skips the services layer, which your architecture allows.
- services → engine (`gateway.js:8`)
- engine → data (`pricing.js:7`)

Nothing imports upward or sideways, and there are no import cycles.

**Enforcement:** `eslint-boundary.cjs` sets up `import/no-restricted-paths` with 6 zones. They cover every upward pair (data←ui, data←services, data←engine, engine←ui, engine←services, services←ui). Downward skips are still allowed, which matches your architecture. `.plumb-line/enforcement.json` points to that config correctly.
- *Caveat:* the linter wasn't run in this audit (dependencies aren't installed and the network is blocked), and I didn't find a CI hook in the fixture. Run `npm ci && npx eslint -c eslint-boundary.config.cjs src` to confirm.

## Priors from config

**Finding P-1 (Medium): nothing loads `config/priors.json`.**
- `pricing.js:35` takes `config` as a parameter, and there is no hardcoded fallback rate. That part is right.
- But no module in `src/` reads `config/priors.json`. Whatever calls these functions can pass any object, so "priors come from `config/`" is a convention, not something the code guarantees. The code can't show where the priors came from.
- The config isn't validated either. If `processingFeeRate` is missing, `pricing.js:40–42` produces `NaN` fee and total but still reports `confidence: 1.0`.
- *Fix:* add one loader that reads and validates `config/priors.json` and is what supplies the `config` argument. Throw an error, or lower the confidence, when `processingFeeRate` is missing or isn't a finite number.

## Lineage on the services output

**Pass on shape.** `gateway.js:44–49` records all four fields you listed:
- `source`
- `recordCount`
- `fieldNames`: computed from `Object.keys(priced)`, not hand-copied
- `configVersion`

**Finding L-1 (Medium): the lineage can't fully reproduce the charge on its own.**
- **Input values aren't recorded.** `lineage` doesn't store the `subtotal` that was passed in. It only appears inside the free-text `provenance` string (`pricing.js:49`), so reproducing the charge means parsing a string.
- **`fieldNames` lists the wrong fields.** It holds the engine's *output* field names (`subtotal, fee, total, currency, provenance, confidence, weightsVersion`), not the *input* fields needed to reproduce the result.
- **The config version can't be looked up.** `configVersion: "1.0.0"` only works if that version can be traced back to a fee rate. `config/priors.json` is a single mutable file with no version history in the code, so once the file changes, `1.0.0` no longer points to a rate.
- **The code comment claims more than the code does.** The comment at `gateway.js:39–43` says lineage "records the full set" needed to reproduce the charge. That isn't true yet for the reasons above.
- *Fix:* add structured inputs, e.g. `inputs: { subtotal, currency }`. Change `fieldNames` to the input fields, or add them alongside. Either record `processingFeeRate` in the lineage or make config versions immutable and addressable.

**Finding L-2 (Low): `source` names the code, not the data.** `"engine/pricing.calculateTotal"` is the function that produced the value. The data comes from whoever called the function, and nothing records who that was. That's acceptable for a stub, but the source should name the caller or request once this is real.

## Provenance and confidence

**Engine (`pricing.js:44–52`): Pass.** It returns provenance, confidence, and `weightsVersion`. A confidence of `1.0` fits a deterministic calculation, but only if the inputs are valid, and nothing checks that (see P-1).

**Services (`gateway.js:51–61`): Pass on labelling.** It marks the result `dataStatus: "simulated"` and `confidence: 0.0`, and prefixes the transaction ID with `stub-`. It doesn't pass the mock result off as real.

**Finding C-1 (Low–Medium): the stub always reports `accepted: true`.**
- `gateway.js:52` hardcodes `accepted: true`. That's a success claim with nothing behind it.
- The response is labelled as simulated, but any caller that only checks `accepted` will go ahead with a charge that never happened.
- *Fix:* return `accepted: null` or `false` while simulated, or have the flag read `dataStatus`.

**UI (`checkout.js:32–39`): Pass.** It passes provenance, confidence, and `weightsVersion` through unchanged.

**Finding C-2 (Low): the UI skips the services layer, so the user sees a value with no lineage.**
- `checkout.js` calls the engine directly. The skip is allowed, but it means the displayed total never goes through the lineage-bearing layer.
- As a result, the checkout display has no `lineage` and no `dataStatus`.
- This is allowed by your rules, but you should know the value the user sees isn't the one the lineage describes.

## Priors version passed along

**Pass.** `config.version` flows engine → `weightsVersion` → services (`weightsVersion` and `lineage.configVersion`) → UI (`weightsVersion`).

**Finding D-1 (Low): a comment misuses "lineage".** The comment at `checkout.js:38` calls `weightsVersion` "the priors version (lineage)". By your definition, lineage is the full set of inputs needed to reproduce a result, and the version is only one part of it. Reword the comment so the two ideas don't get mixed up.

## Other correctness issues (outside the principles)

- **F-1 (Low): money is computed in floating point.** `subtotal * feeRate` (`pricing.js:41`) is never rounded, so `fee` and `total` can carry float noise into `chargedAmount`. Use integer minor units (cents) or round explicitly.
- **F-2 (Low): JPY is formatted with 2 decimals.** `checkout.js:33` always uses `toFixed(2)`, but JPY has no minor unit. Also, `CURRENCY_SYMBOLS` is defined in `rates.js` but never used.
- **Stale comment:** the "Allowed imports: engine only" comment at `checkout.js:5` is stricter than your architecture, which also allows ui → data. That's harmless, but the comment and the declared rule differ.

## Prioritized actions

1. **L-1:** record the input values in structured form, list input field names, and make the config version traceable to a fee rate. Then correct the comment at `gateway.js:39–43`.
2. **P-1:** add one loader that reads and validates `config/priors.json`, and fail or lower the confidence when the fee rate is missing.
3. **C-1:** stop returning `accepted: true` from the stub.
4. Run the boundary lint in CI, and run it once locally with dependencies installed.
5. Then the low items: F-1, F-2, C-2, D-1, L-2.