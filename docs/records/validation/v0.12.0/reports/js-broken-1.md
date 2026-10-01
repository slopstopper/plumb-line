report-format: v4
scope:               <harness>/fixtures/js-broken-1 (repository)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied by the owner in the invocation): layers `ui -> services -> engine -> data`, one-way, non-adjacent downward skips allowed; priors come from `config/`; the services layer is the lineage-bearing output (source identity, record count, field names, config/version); outputs carry provenance and confidence and propagate the priors version. No source-truth layer was declared, so P1 — Source-truth layer is not applied to any layer (none is inferred), and P1 — Source-truth layer coverage is `partial`. No composition root was declared. The repo's own `eslint-boundary.cjs` zones match the declared direction.

Traversal plan: read every source, config and enforcement file (9 files); skip `package-lock.json` (dependency pins, no product logic). There are no test files in scope.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/data/rates.js` | 7-8 | — (module scope) | violation | The bottom layer (`data`) imports and re-exports `buildCheckoutDisplay` from the top layer (`ui`), against the declared downward-only direction; this also makes a cycle `ui -> engine -> data -> ui`. The repo's own zone `{ target: "./src/data", from: "./src/ui" }` forbids it, so the boundary lint is either not run or not gating. | Remove the import and re-export (the "not dead code" re-export exists only to keep the leak alive); wire `eslint-boundary.config.cjs` into a gate that fails the build. | P2 — One-way layering |
| `src/engine/pricing.js` | 9, 42, 50 | `calculateTotal` | violation | The fee prior is hardcoded as `const FEE = 0.029` and used in the calculation; the injected `config.processingFeeRate` is never read, so changing `config/priors.json` has no effect. | Compute the fee from `config.processingFeeRate` (validate that it is present), and delete the module constant. | P5 — Injectable priors |
| `src/engine/pricing.js` | 52 | `calculateTotal` | violation | `weightsVersion: config.version` credits the result to the injected priors version, but the fee came from the hardcoded constant rather than that config. If the priors change (e.g. rate 0.03 at v1.1.0), the output would claim v1.1.0 while still using 0.029. | Stamp the version only from the config the calculation actually read; this is fixed together with the hardcoded-prior row above. | P3 — Confidence + provenance |
| `src/engine/pricing.js` | 30 | `calculateTotal` | violation | The docstring says "The fee rate comes exclusively from the injected config — never hardcoded here", but the code does the opposite (line 9, 42). The doc states a guarantee the code does not provide. | Make the claim true by fixing the code, or correct the docstring until it is fixed. | P6 — Maturity vocabulary |
| `config/priors.json` | 4 | — | violation | `description` says "All weights are explicit config, not hardcoded constants", but the only prior it defines (`processingFeeRate`) is shadowed by a hardcoded constant in the engine. | Keep the description only once the engine reads the value; until then, state that it is `partial`. | P6 — Maturity vocabulary |
| `src/engine/pricing.js` | 51 | `calculateTotal` | needs-review | `confidence: 1.0` is a literal. It is not derived from the confidence of any input (`subtotal` arrives with none), and it is asserted over a fee whose rate differs from the declared priors. It may be defensible for exact arithmetic on trusted input, but that is not established. | Derive confidence from the input's confidence, or document why deterministic arithmetic justifies 1.0, and inject that as a prior if it is a judgment call. | P3 — Confidence + provenance |
| `src/services/gateway.js` | 16, 21 | `submitPayment` | violation | `chargedAmount` is the fixed `MOCK_CHARGED_AMOUNT = 42.0`, whatever `subtotal`, `currency` or `config` are (the engine is never called). The value leaves the function with no mock marker, looking like a real charged amount. The `stub-` prefix on `transactionId` is the only hint, and it labels a different field. | Label the output as mock (e.g. a `derivedFromMock`/`mock: true` field) and keep it out of real output paths unless the caller opts in explicitly; otherwise compute the amount through `engine/pricing.js`. | P4 — Quarantined fakery |
| `src/services/gateway.js` | 19-24 | `submitPayment` | violation | The declared lineage-bearing output records no lineage: no source identity, no record count, no field names, no config/version. `config` is accepted and ignored, so the priors version is not propagated either. `transactionId` is time-derived (`Date.now()`), which makes the result non-reproducible. | Add a lineage field that records the source identity, the record count, the input field names and `config.version`; this is the declared rule for this layer. | P8 — State-first lineage |
| `src/services/gateway.js` | 19-24 | `submitPayment` | violation | The declared rule says outputs carry provenance and confidence, but this output has neither; a mock value (42.0) is presented as clean truth. | Add provenance (it is a stub, and where the amount came from) and confidence (low or none for a mock) to the result. | P3 — Confidence + provenance |
| `src/ui/checkout.js` | 31-37 | `buildCheckoutDisplay` | violation | The output passes `provenance` and `confidence` through from the engine but drops `weightsVersion`, so the displayed result does not carry the priors version, which the declared architecture says outputs propagate. | Pass `weightsVersion` (the priors version) through into `CheckoutDisplay`. | P5 — Injectable priors |
| `src/services/gateway.js` | 20 | `submitPayment` | advisory | `accepted: true` is unconditional, so the payment path cannot express a rejected or declined outcome. Rejection is not declared in the architecture. No output shape practices a reject/null outcome (the engine only throws on an unsupported currency), so this is an adoption gap, not a confirmed violation. | Decide whether payment rejection is in scope; if so, declare it and add a reject path to the result shape. | spine — null-result expressibility |
| `src/engine/pricing.js`, `src/ui/checkout.js`, `src/services/gateway.js` | — | — | advisory | No output has a versioned, validated contract (no version constant, validator or canonical key list). `PricingResult` and `CheckoutDisplay` are JSDoc typedefs only, and `submitPayment` returns an untyped `object`. Contracts are not declared or practiced anywhere, so this is reported once as an adoption gap. | Give each public output a version constant, a validator and a key list, starting with the lineage-bearing service output. | P7 — Contracted outputs |
| `src/engine/pricing.js`, `src/ui/checkout.js`, `src/services/gateway.js` | — | — | advisory | There is no golden baseline, and no tests at all, pinning any derived output, so fee or total drift would go unnoticed. Not declared or practiced anywhere; reported once as an adoption gap. | Pin `calculateTotal` outputs for a few subtotals and currencies against the current priors version, and require an explanation when they drift. | P9 — Golden baseline + explain-the-drift |
| — | — | — | advisory | The declared architecture names the layer direction and the lineage bearer but no source-truth layer or composition root, and no file uses the maturity vocabulary (the gateway is a stub, described as "simulates", but is not labelled `mock`). P1 — Source-truth layer cannot be checked without inventing a layer. | Declare the source-truth layer (and composition root, if any) in a ruleset file; mark `submitPayment` as `mock`. | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `calculateTotal` -> `PricingResult` (`src/engine/pricing.js`) | YES — free-text string naming the hardcoded FEE | YES — literal 1.0, not derived (needs-review) | PARTIAL — `weightsVersion` only, and it is misattributed; no source or field names; engine is not a declared bearer | NO — JSDoc typedef only (advisory) | NO — throws on unsupported currency; no null outcome in the shape | NO (advisory) |
| `buildCheckoutDisplay` -> `CheckoutDisplay` (`src/ui/checkout.js`) | YES — passed through from engine | YES — passed through from engine | NO — drops `weightsVersion`; priors version declared to propagate (P5 — Injectable priors violation) | NO — JSDoc typedef only (advisory) | NO — inherits the engine throw only | NO (advisory) |
| `submitPayment` -> untyped object (`src/services/gateway.js`) | NO — declared rule (P3 — Confidence + provenance violation) | NO — declared rule (P3 — Confidence + provenance violation) | NO — declared bearer (P8 — State-first lineage violation) | NO — untyped `object` (advisory) | NO — always `accepted: true` (advisory, rejection adopted nowhere) | NO (advisory) |
| `CURRENCY_SYMBOLS` / `SUPPORTED_CURRENCIES` (`src/data/rates.js`) | NO — static literal table with no source note; not flagged (reference constants, not a declared rule) | n/a — static reference data | n/a — static reference data, not a derived output | NO — no contract (covered by the advisory) | n/a — a constant table | NO (covered by the advisory) |

```
src/data/rates.js                read
src/engine/pricing.js            read
src/services/gateway.js          read
src/ui/checkout.js               read
config/priors.json               read
eslint-boundary.cjs              read
eslint-boundary.config.cjs       read
.plumb-line/enforcement.json     read
package.json                     read
package-lock.json                not-read (dependency lockfile, no product logic)
```

```
coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. The boundary
lint was read, not executed (no node_modules; the target is not modified), and P1 — Source-truth layer
coverage is partial because no source-truth layer was declared.
```

14 findings: 9 violations, 1 needs-review, 4 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

I ran the checker on the text above, saved as `<harness>/work/js-broken-1/report.txt`, and it passed. A report file named `.md` was blocked, so the checker input is `.txt`. I did not write `plumb-line-audit.md`, because no one was available to answer the save question. I made no handoff to remediate or bootstrap either, since that also needs someone to accept it. The target directory was not changed.

## Decisions needed
1. Is rejecting a payment in scope for `submitPayment`? My recommendation is yes: declare it, which would turn the spine advisory into a violation to fix.
2. Which layer is the source-truth layer? My recommendation is to declare `data` explicitly, if that is what you intend, so that P1 — Source-truth layer can be audited next time.