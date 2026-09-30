# Plumb-line audit: `./fixture` (js-payments-service-fixture)

**How I ran it:** the `plumb-line` audit skill isn't available in this session, so I did the audit by hand against the architecture you declared. I read all 4 source files, the priors, the enforcement manifest and the generated ESLint boundary config. I also ran the service and UI code directly with the real priors, a JPY input, a fractional subtotal and an empty config.

**Enforcement gate not run:** the boundary lint couldn't execute. `node_modules/eslint` 10.10.0 crashes on load (`SyntaxError: Unexpected token ')'` at `lib/services/suppressions-service.js:58`), and reinstalling was blocked because npm network access is denied. The layering results below come from reading the imports and the config, not from a passing lint run.

## Verdict

The layer structure, the priors and the lineage shape all conform. The main problem is that the code doesn't fail loudly: when priors are missing, the service quietly returns a charge whose lineage has lost its config version. There are also two money-correctness defects.

| # | Principle | Severity | Finding |
|---|---|---|---|
| 1 | Lineage / priors propagation | **High** | Missing priors give a NaN charge with no config version, still `accepted: true` |
| 2 | Lineage content | Medium | `lineage.fieldNames` lists the engine's output keys, not the inputs you'd need to reproduce the result |
| 3 | Output correctness | Medium | The charged amount is an unrounded float |
| 4 | Output correctness | Low | Every currency is shown with 2 decimals, which is wrong for JPY |
| 5 | Confidence semantics | Low | Service confidence is 0.0, which throws away the engine's 1.0 |
| 6 | Layering docs | Low | The UI header comment is stricter than the declared architecture |
| 7 | Enforcement | Info | The boundary gate can't currently run (broken install) |

## Principle 2: one-way layering (ui → services → engine → data, skips allowed)

**Pass.** The actual imports:
- `src/ui/checkout.js:8` imports engine. This skips services, which is allowed.
- `src/services/gateway.js:8` imports engine.
- `src/engine/pricing.js:7` imports data.
- `src/data/rates.js` imports nothing.

No import points upward or sideways.

The generated `eslint-boundary.cjs` has the zone direction right: `target` is the lower layer, `from` is the upper one. It covers all 6 upward pairs, so downward skips are allowed. The config is correct; it just can't run right now (finding 7).

**Finding 6 (Low):** `src/ui/checkout.js:4-5` says "Allowed imports: engine only; never imports services or data." The declared architecture lets ui import services and data too. The comment describes a stricter rule than the one enforced, which will mislead anyone editing the file later. Align it with the declared rule, or add a zone if the stricter rule is what you actually want.

## Priors come from `config/`

**Pass on sourcing.** `processingFeeRate` and `version` live only in `config/priors.json`. The engine reads them from the injected `config` (`pricing.js:40,51`) and doesn't hardcode any weights. The currency table in `data/rates.js` is reference data, not a prior. The literal confidence values (`1.0`, `0.0`) aren't model weights.

**Finding 1 (High):** nothing checks the injected priors. Calling it with `{}` returned:

```
chargedAmount: null (NaN), accepted: true, confidence: 0,
lineage: { source, recordCount: 1, fieldNames: [...] }   // configVersion silently absent
weightsVersion: absent
```

- `pricing.js:40-51` accepts `processingFeeRate` and `version` being undefined, and still reports `confidence: 1.0`.
- `gateway.js:48,60` then passes `undefined` through, so the output looks like it has complete lineage but carries no config version.

**Fix:** in `calculateTotal`, check that `config.version` is a non-empty string, `processingFeeRate` is a finite number ≥ 0, and `subtotal` is finite, and throw if any check fails. It already throws for unsupported currencies, so this matches the existing style.

## Services are the lineage-bearing output

**Pass on shape.** `gateway.js:44-49` records all 4 declared fields:
- `source`: `"engine/pricing.calculateTotal"`
- `recordCount`: `1`
- `fieldNames`
- `configVersion`

It also carries `provenance`, `confidence`, `dataStatus: "simulated"` and `weightsVersion`. With valid priors it produced `configVersion: "1.0.0"` and a provenance string that includes the subtotal and fee rate.

**Finding 2 (Medium):** `fieldNames: Object.keys(priced)` lists the engine's *output* keys (`subtotal, fee, total, currency, provenance, confidence, weightsVersion`). It doesn't identify the *inputs* needed to reproduce the charge (`subtotal`, `currency`, and the priors). The subtotal value only survives inside the free-text `provenance` string. The comment at `gateway.js:39-43` rightly says provenance text isn't enough to reproduce a result, but the structured lineage leans on it for exactly that. Add input fields (e.g. `inputs: { subtotal, currency }`) or make `fieldNames` name the input fields.

`source` names a function rather than a data source. That's defensible for a stub with no upstream record set, but note it as a placeholder to replace when the real gateway is wired up.

## Provenance, confidence and priors-version propagation

**Pass.** The engine sets all three (`pricing.js:49-51`). The service wraps the provenance and carries the version twice (`gateway.js:56-60`). The UI passes all three through (`checkout.js:36-38`). No layer drops them when the priors are valid.

**Finding 5 (Low):** the service hard-sets `confidence: 0.0` (`gateway.js:57`). The label is honest (`dataStatus: "simulated"`, "stub" provenance), but it replaces the engine's 1.0 rather than combining with it. That means 0 is covering two different things: "calculated correctly but not confirmed by a gateway" and "garbage" (see finding 1). Consider keeping the engine's confidence separately, or documenting what 0 means.

## Output correctness (found while checking lineage)

- **Finding 3 (Medium):** `pricing.js:41-42` uses raw float arithmetic. `submitPayment(19.99, "USD")` charges `20.569709999999997`. A value like that passed to a payment gateway, and recorded as reproducible lineage, needs a defined rounding rule (e.g. integer minor units plus a rounding mode recorded in priors).
- **Finding 4 (Low):** `checkout.js:33` uses `toFixed(2)` for every currency, giving `"JPY 1029.00 (includes fee of 29.00)"`, but JPY has no minor unit. `CURRENCY_SYMBOLS` is exported but never used. Put minor-unit counts next to it in `data/rates.js`.

## Enforcement

- **Finding 7 (Info):** `.plumb-line/enforcement.json` points to `eslint-boundary.config.cjs`, and that config is correct. But the installed ESLint crashes on load, so the layering rule currently isn't enforced at all. Reinstall with `npm ci` in `fixture/` and confirm it exits 0. As a check that it catches violations, add a temporary upward import (engine → services, or data → ui) and confirm the lint exits non-zero. I set up that probe, but it couldn't run because of the crash.

## Recommended order

1. Finding 1: validate priors and inputs in the engine.
2. Finding 7: repair the ESLint install so the boundary rule is enforced again.
3. Finding 3: add a money rounding rule.
4. Finding 2: add input fields to the lineage.
5. Findings 4, 5 and 6.
