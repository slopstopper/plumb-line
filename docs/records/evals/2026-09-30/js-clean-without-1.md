I've audited `./fixture`, but not with the plumb-line audit skill. That skill isn't in this session's skill list and isn't in `.claude/`, so I checked the code by hand against the architecture you declared. The method is below so you can compare it with what the skill would do.

# Audit report: `fixture/` (js-payments-service-fixture)

## Method

- **Code reviewed:** I read all 4 source files plus the config and enforcement files: `src/{ui,services,engine,data}`, `config/priors.json`, `eslint-boundary*.cjs` and `.plumb-line/enforcement.json`. I skipped `node_modules`.
- **Import graph:** I checked every import by hand. There are no dynamic `import()` or `require` calls in `src/`.
- **Automatic enforcement didn't run.** The boundary lint and an upward-import test file I added to a copy of `src/` (to confirm the lint catches violations) both crashed before linting. The installed ESLint 10.10.0 is corrupted: `node_modules/eslint/lib/services/suppressions-service.js:58` is missing lines, which causes `SyntaxError: Unexpected token ')'`. I couldn't reinstall because the sandbox blocks the npm registry. I didn't change anything in the fixture.

## Summary

| # | Finding | Principle | Severity |
|---|---|---|---|
| 1 | The boundary lint can't run, so layering isn't actually enforced | Layering enforcement | **High** |
| 2 | The payment stub reports `accepted: true` for a payment no gateway confirmed | Provenance / no laundered data | **Medium** |
| 3 | A malformed priors config fails silently (`NaN` / `undefined`) | Priors from config | **Medium** |
| 4 | The lineage has all four fields, but they aren't enough to reproduce the charge | Lineage at the service layer | **Low–Medium** |
| 5 | Nothing in the code loads `config/priors.json` | Priors from config | Low |
| 6 | Money is calculated in floating point with no rounding | Correctness (outside the principles) | Low |

**Layer direction:** no violations. **Provenance, confidence and priors version:** carried through at every layer.

## Layering: one-way ui → services → engine → data (passes)

| From | To | Direction | Verdict |
|---|---|---|---|
| `src/ui/checkout.js:8` | `engine/pricing.js` | down, skipping services | Allowed (you allow downward skips) |
| `src/services/gateway.js:8` | `engine/pricing.js` | down | OK |
| `src/engine/pricing.js:7` | `data/rates.js` | down | OK |
| `src/data/rates.js` | nothing | n/a | OK |

The generated rules in `eslint-boundary.cjs:4-11` are correct and complete. Their 6 zones block all 6 upward pairs, and none of them block the allowed skip from ui to engine.

### Finding 1: the boundary lint can't run (High)

`.plumb-line/enforcement.json` points at `eslint-boundary.config.cjs`, but the installed ESLint crashes on load. As things stand, any upward import would get through. The code is clean today only because I checked it by hand.

**Fix:** reinstall with `rm -rf node_modules && npm ci`, then rerun the lint. Add a test that deliberately contains an upward import, such as `data → ui`, so a broken or missing linter fails loudly instead of passing silently.

## Provenance, confidence and priors version (passes, with one issue)

- **Engine** (`pricing.js:44-52`): returns `provenance`, `confidence: 1.0` (the calculation is deterministic) and `weightsVersion: config.version`.
- **Services** (`gateway.js:51-61`): passes all three through, sets `confidence: 0.0`, and sets `dataStatus: "simulated"`.
- **UI** (`checkout.js:36-38`): passes through `provenance`, `confidence` and `weightsVersion`.

### Finding 2: `accepted: true` is made up (Medium)

`gateway.js:52` hard-codes `accepted: true` even though no gateway was called. The amount is correctly labelled as simulated with zero confidence, but `accepted` is a plain boolean with no label of its own. Any caller that branches on `if (resp.accepted)` treats a simulated payment as a confirmed one. The response contradicts itself: accepted, but with zero confidence.

**Fix:** use `accepted: null` or `"simulated"`, or make callers check `dataStatus` before trusting `accepted`.

## Priors come from `config/` (partial)

The engine takes its fee rate only from the injected config (`pricing.js:40`), and there's no hard-coded fallback. `config/priors.json` holds both `version` and `processingFeeRate`.

### Finding 3: bad config fails silently (Medium)

`calculateTotal` never checks the config. If `processingFeeRate` is missing, `fee` and `total` become `NaN`. If `version` is missing, `weightsVersion` and `lineage.configVersion` become `undefined`. Either result still comes back with `confidence: 1.0` from the engine, so the untraceable output looks correct.

**Fix:** throw an error when `config.version` isn't a string or `processingFeeRate` isn't a finite number, the same way unsupported currencies already throw (`pricing.js:36-38`).

### Finding 5: nothing loads the priors file (Low)

No code in `src/` reads `config/priors.json`; every entry point expects the caller to pass the config in. Nothing in this codebase guarantees the priors really come from `config/`. **Fix:** add one small loader (with the validation from Finding 3) and have callers use it.

## Lineage at the service layer (nominal pass)

The lineage object in `gateway.js:44-49` has all four fields you listed: `source`, `recordCount`, `fieldNames` and `configVersion`.

### Finding 4: the lineage can't reproduce the charge (Low–Medium)

Your definition says the lineage must hold the inputs needed to reproduce the result, and this one only partly does:

- **`source`** is a function name (`"engine/pricing.calculateTotal"`), not the identity of the input data.
- **`fieldNames`** is `Object.keys(priced)`, so it lists output fields (`subtotal`, `fee`, `total`, …), not input fields.
- **The inputs themselves** (`subtotal`, `currency`) aren't in the lineage. `subtotal` only appears inside the free-text `provenance` string, and `currency` only at the top level of the response.
- **`recordCount: 1`** is hard-coded, not counted.

**Fix:** record the actual inputs, e.g. `inputs: { subtotal, currency }` alongside `configVersion`. Then someone can rerun `calculateTotal` from the lineage alone.

Separately, the UI skips services and calls the engine directly, which is allowed. That means the total shown at checkout never carries a lineage record, only provenance and version. This isn't a violation, since you only require lineage on service output, but it's worth knowing.

## Finding 6: floating-point money (Low, outside the principles)

`pricing.js:41-42` computes `subtotal * 0.029` in floating point and never rounds. Rounding only happens for display (`checkout.js:33`), so `chargedAmount` can carry values smaller than a cent. Use integer minor units (cents), or round explicitly according to a documented rule.

## Priority fixes

1. Repair `node_modules` and confirm the boundary lint runs and catches a deliberate upward import.
2. Make `calculateTotal` validate the priors config and throw on bad input.
3. Stop reporting `accepted: true` for payments no gateway confirmed.
4. Put the actual inputs in the gateway lineage.

If the plumb-line audit skill is installed under another name or somewhere else, tell me where and I'll rerun the audit through it.
