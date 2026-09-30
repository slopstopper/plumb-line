# Plumb-line audit: `./fixture` (js-payments-service-fixture)

**Method:** There is no plumb-line audit skill in this session. The only skills available are dataviz, code-review, simplify, security-review and a few others. So this report does not come from the skill. I audited the code by hand against the architecture you declared and the principles the fixture itself points to (the boundary config says "Principle 2 = one-way layering"). I read all 9 files, reviewed the boundary config by hand, and ran the engine and service on edge-case inputs in a temporary copy. I could not run the ESLint boundary check: `node_modules` isn't installed and the sandbox blocks registry.npmjs.org. The fixture was not modified.

## Summary

| # | Severity | Principle | Finding |
|---|---|---|---|
| F1 | **High** | Confidence / provenance honesty | The engine returns `confidence: 1.0` when its result is `NaN`, and `weightsVersion` is `undefined` when the config is missing or malformed |
| F2 | **Medium** | Lineage (service layer) | `lineage` has all four declared keys but can't reproduce the charge on its own: it lacks input values, and `fieldNames` lists output keys |
| F3 | **Medium** | No mock laundering | The stub hardcodes `accepted: true`, an unqualified success claim beside `confidence: 0` |
| F4 | Low | Domain correctness | `chargedAmount` isn't rounded to the currency's minor unit (probe gave `10.30029` USD); negative subtotals are accepted |
| F5 | Low | Enforcement | The boundary rules are correct but unverified: the dependencies aren't installed and nothing runs them automatically |
| F6 | Info | Layering docs | The `ui` header says "Allowed imports: engine only", which is stricter than the declared rules |

**Passes:** layer direction, priors injection, and propagation of provenance, confidence and priors version on every output.

## Passing checks

**Layer direction (ui → services → engine → data, downward skips allowed)**
- `src/ui/checkout.js:8` imports engine. Skipping services is an allowed downward skip.
- `src/services/gateway.js:8` imports engine.
- `src/engine/pricing.js:7` imports data.
- `src/data/rates.js` imports nothing.
- No upward or sideways imports.

**Priors come from `config/`**
- The fee rate is read only from the injected `config.processingFeeRate` (`pricing.js:40`), which matches `config/priors.json`.
- There are no hardcoded weights. The `1.0` and `0.0` literals are confidence claims, not priors.

**Provenance, confidence and priors version on outputs**
- Engine: `pricing.js:49-51`.
- Service: `gateway.js:56-60`. Service confidence drops to `0.0` and `dataStatus: "simulated"` is set.
- UI passes through all three: `checkout.js:36-38`.

**Boundary config** (`eslint-boundary.cjs:4-11`)
- All 6 upward pairs are forbidden: data←{ui, services, engine}, engine←{ui, services}, services←ui.
- Downward skips are left open. The zone semantics (target = importing file, from = forbidden source) are correct.

## Findings

### F1 — High: confidence doesn't reflect whether the inputs were valid
`src/engine/pricing.js:35-52` checks the currency but not the config or the subtotal. Probe result:

```
calculateTotal(100, "USD", {})
→ { fee: NaN, total: NaN, confidence: 1, weightsVersion: undefined,
    provenance: "...processingFeeRate=undefined" }
```

- A NaN total is reported with full confidence, and the priors version it passes on is `undefined`.
- The UI would render `"USD NaN (includes fee of NaN)"`.
- The service still returns a lineage record, with `configVersion: undefined`.

**Fix:** throw (or return confidence 0 with an explicit error status) when `processingFeeRate` isn't a finite number in [0, 1), when `version` is missing, or when `subtotal` isn't a finite, non-negative number. Also, nothing in `src/` loads `config/priors.json`. Every caller builds `config` itself, so there's no single validated place where priors enter the code.

### F2 — Medium: the lineage record can't reproduce the charge on its own
The declared rule is that the service result must record the inputs needed to reproduce it. `gateway.js:44-49` has problems with three of the four keys:

- **`source: "engine/pricing.calculateTotal"`** names the function that did the calculation, not where the input came from (which order or request the subtotal belongs to).
- **`fieldNames: Object.keys(priced)`** lists the *output* keys: `subtotal, fee, total, currency, provenance, confidence, weightsVersion`. Two of those, `provenance` and `confidence`, are metadata rather than inputs. The actual reproduction inputs are `subtotal`, `currency` and `config.processingFeeRate`.
- **Input values:** `lineage` doesn't include them. `subtotal` appears only inside the free-text `provenance` string. `currency` is a separate top-level field.
- **`recordCount: 1`** is a hardcoded literal. That's harmless for a single charge, but it isn't derived from anything.

The code comment at `gateway.js:41-43` claims more completeness than the record delivers.

**Fix:** record `inputs: { subtotal, currency }`, input field names `["subtotal", "currency", "processingFeeRate"]`, `configVersion`, and a real source identifier from the caller (for example, an order ID).

### F3 — Medium: the stub claims acceptance
`gateway.js:52` returns `accepted: true` without qualification. `dataStatus: "simulated"` and `confidence: 0` label the result honestly, but `provenance` only describes `chargedAmount`. A caller that branches on `accepted`, which is the usual check, will treat a simulated charge as a confirmed one.

**Fix:** use `accepted: null` or `"simulated"` in stub mode, or make the provenance and status cover `accepted` explicitly.

### F4 — Low: currency precision and sign checks
The fee isn't rounded to the currency's minor unit (JPY has none). Probe results:

- `submitPayment(10.01, "USD", …)` gives `chargedAmount: 10.30029`.
- A negative subtotal is accepted: `total: -51.45` JPY, with confidence 1.

`toFixed(2)` in `checkout.js:33` only fixes the display, and it's wrong for JPY.

### F5 — Low: the boundary check isn't verified or wired in
`.plumb-line/enforcement.json` points at `eslint-boundary.config.cjs`, and the rules look correct. However:

- `node_modules` is missing, so I couldn't install or run the check (registry access is blocked here).
- `package.json` has no `lint` script, so nothing runs the check routinely.

Recommend adding `"lint:boundary": "eslint -c eslint-boundary.config.cjs src"` and running it in CI.

### F6 — Info: documentation drift
`checkout.js:4-5` says "never imports services or data" and "Allowed imports: engine only". The declared architecture allows ui to import services and data. The code complies either way. Either make the header match the declared rules, or add a deliberate stricter zone to the boundary config.

## Recommended order
Fix F1 first: validate priors and inputs, and make confidence depend on them. Then F2 and F3, which make the service-layer lineage and status honest. F4–F6 are cleanup.