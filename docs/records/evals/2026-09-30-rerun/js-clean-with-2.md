report-format: v4
scope:               fixture/ (repository: ./fixture)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P1 — Source-truth layer      P6 — Maturity vocabulary   P8 — State-first lineage
P2 — One-way layering        P7 — Contracted outputs    P9 — Golden baseline + explain-the-drift
P3 — Confidence + provenance
spine — null-result expressibility
```

**Declared architecture (supplied by the project owner in the invocation):** layers `ui -> services -> engine -> data`, one-way, with non-adjacent downward skips allowed; priors come from `config/`; the services output is the lineage-bearing output (source identity, record count, field names, config/version); outputs carry provenance and confidence and pass on the priors version. No source-truth layer was named, so this audit does not assume one, and its coverage of P1 — Source-truth layer is partial.

**Presence pass:** all imports go downward. `ui -> engine` is an allowed skip, `services -> engine` and `engine -> data` are adjacent. `eslint-boundary.cjs` encodes the same direction and forbids nothing the declaration allows. The only prior (`processingFeeRate`) lives in `config/priors.json` and is injected. The gateway stub is labelled (`dataStatus: "simulated"`, `confidence: 0.0`, `stub:` provenance, `stub-` transaction id). No mock value is presented as real, no maturity is overstated, there is no baseline drift, and there are no tests, so none were changed to pass.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `fixture/src/services/gateway.js` | 51-52 | `submitPayment` | advisory | the stub can only return `accepted: true`, so a declined or inconclusive charge cannot be expressed; rejection is not declared or practiced anywhere, so this is an adoption gap | add a reject/inconclusive path, such as `accepted: false` with a reason, before a real gateway replaces the stub | spine — null-result expressibility |
| `fixture/src/services/gateway.js`, `fixture/src/engine/pricing.js`, `fixture/src/ui/checkout.js` | — | — | advisory | output shapes are JSDoc typedefs only: no version constant, validator, or canonical key list; not declared or practiced anywhere, so this is an adoption gap | add a versioned contract with a validator, starting with `GatewayResponse` as the lineage-bearing output | P7 — Contracted outputs |
| `fixture/` | — | — | advisory | no tests or golden baselines pin any output, so a change to fee or total values would not be detected or explained; not adopted anywhere | add a golden baseline for `calculateTotal` and `submitPayment` at a fixed priors version, with a drift-explanation rule | P9 — Golden baseline + explain-the-drift |
| `fixture/` | — | — | advisory | the declared architecture does not name the source-truth layer (the bottom layer `data` is not declared as such), so that rule is not written down (P6 — Maturity vocabulary) | declare the source-truth layer (for example, `data`) in the ruleset, such as `AGENTS.md` or `CLAUDE.md` | P1 — Source-truth layer |
| `fixture/package.json` | 1-2 | — | needs-review | the boundary rule exists (`eslint-boundary.config.cjs`, registered in `.plumb-line/enforcement.json`), but no npm script in scope runs it; a hook or CI outside `fixture/` may run it, which this audit could not check | wire the boundary lint into a `lint` script and a pre-commit or CI gate, or confirm an existing hook runs it | P2 — One-way layering |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `calculateTotal` → `PricingResult` (`fixture/src/engine/pricing.js`) | YES — derivation string with subtotal and fee rate | YES — `1.0`, deterministic arithmetic over injected config | PARTIAL — `weightsVersion` only; not a declared lineage bearer, so not required | NO — JSDoc typedef only (adoption gap) | PARTIAL — throws on unsupported currency; no non-exception null | NO — none (adoption gap) |
| `submitPayment` → `GatewayResponse` (`fixture/src/services/gateway.js`) | YES — `stub:` string chained from engine provenance | YES — `0.0` plus `dataStatus: "simulated"` | YES — declared bearer: `lineage` has `source`, `recordCount`, `fieldNames`, `configVersion` | NO — JSDoc typedef only (adoption gap) | NO — `accepted` is always `true` (advisory) | NO — none (adoption gap) |
| `buildCheckoutDisplay` → `CheckoutDisplay` (`fixture/src/ui/checkout.js`) | YES — passed through from engine | YES — passed through from engine | PARTIAL — `weightsVersion` passed through; not a declared lineage bearer | NO — JSDoc typedef only (adoption gap) | PARTIAL — engine exception propagates; no null display state | NO — none (adoption gap) |

```
fixture/src/ui/checkout.js              read
fixture/src/services/gateway.js         read
fixture/src/engine/pricing.js           read
fixture/src/data/rates.js               read
fixture/config/priors.json              read
fixture/eslint-boundary.cjs             read
fixture/eslint-boundary.config.cjs      read
fixture/.plumb-line/enforcement.json    read
fixture/package.json                    read
fixture/package-lock.json               not-read (generated dependency lockfile)
coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. Git history
could not be inspected in this sandbox, and hooks or CI outside fixture/ were not examined.
```

5 findings: 0 violations, 1 needs-review, 4 advisory
format-validation: scripts/check_report_format.py v6 — clean

---

The audit found no violations. The services output meets the declared lineage rule: `submitPayment` records the source, record count, field names and config version. Every output carries provenance and confidence and passes on the priors version. The five open items are gaps in what the project has adopted, plus one point that could not be checked from `fixture/`: whether anything actually runs the boundary lint.

The report has not been saved. Do you want it written to `plumb-line-audit.md`? After that, I can hand the findings to `plumb-line-remediate` to apply them, starting with a reject path for `submitPayment` and a versioned contract for `GatewayResponse`. Or I can run `plumb-line-bootstrap` to connect the boundary lint to a script and a pre-commit gate.