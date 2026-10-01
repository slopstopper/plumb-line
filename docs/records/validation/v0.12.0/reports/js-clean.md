report-format: v4
scope:               <harness>/fixtures/js-clean (repository)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied in the invocation): layers ui -> services -> engine -> data, one-way, with downward skips over a layer allowed; priors come from `config/`; the services layer's output is the one that must carry lineage (source identity, record count, field names, config/version); outputs carry provenance and confidence and pass the priors version along. The invocation names no source-truth layer, so P1 — Source-truth layer is checked only in part (see the advisory row and the coverage map).

Traversal plan: 10 in-scope files. I read the 4 source files, the priors config, the enforcement manifest, both boundary-rule files and `package.json` in full. I skipped `package-lock.json`, a generated dependency lockfile with no product logic. The scope has no test files, so check 10 (a test changed to pass) had nothing to examine.

Presence pass, with no findings: all three imports go down the layers (`src/ui/checkout.js` imports engine, `src/services/gateway.js` imports engine, `src/engine/pricing.js` imports data). `eslint-boundary.cjs` blocks all six upward edges, which enforces P2 — One-way layering. The fee rate comes from injected config (`config/priors.json`, versioned `1.0.0`), so P5 — Injectable priors holds. The stub gateway labels its own output (`dataStatus: "simulated"`, `confidence: 0.0`, a provenance string that starts with `stub:`), and no export path in scope uses that value, so P4 — Quarantined fakery holds. No comment or doc claims more maturity than the code has, and the gateway calls itself a stub (P6 — Maturity vocabulary). No derived value drops its confidence or provenance on the way down (P3 — Confidence + provenance).

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/services/gateway.js` | 44-49 | `submitPayment` | needs-review | The lineage object has all four declared keys (source, recordCount, fieldNames, configVersion). But the input values needed to rerun the charge are not stored as fields: `subtotal` appears only inside the free-text `provenance` string. `fieldNames` lists the keys of the priced record, not its values. | Owner to confirm whether the four declared keys are enough. If not, add the structured inputs (`subtotal`, `currency`) to `lineage` so `chargedAmount` can be regenerated without parsing text. | P8 — State-first lineage |
| `src/services/gateway.js` | 51-52 | `submitPayment` | advisory | The gateway result always has `accepted: true` and cannot express a decline or an inconclusive outcome. Only an unsupported currency throws, from upstream. Rejection is not declared or practised anywhere in the code, so this is an adoption gap, not a violation. | When a real gateway replaces the stub, add a declined/inconclusive outcome to the result shape and a test that exercises it. | spine — null-result expressibility |
| — | — | — | advisory | No public output has a versioned, validated contract. There are JSDoc typedefs only: no validator, no version constant, no canonical key list. Contracts are not declared or practised anywhere, so this is reported once as an adoption gap. | Give `GatewayResponse` (the lineage-bearing output) a version constant, a key list and a validator first. | P7 — Contracted outputs |
| — | — | — | advisory | No golden baseline pins any derived output (the total, the fee or the charged amount), so a change to `processingFeeRate` would change every result silently. Baselines are not adopted anywhere, so this is reported once as an adoption gap. | Pin a small golden baseline for `calculateTotal` and `submitPayment`, and require a recorded reason whenever it changes. | P9 — Golden baseline + explain-the-drift |
| — | — | — | advisory | The declaration names no source-truth layer (P1 — Source-truth layer). The audit does not guess one, so it could not check for derived or fake logic inside that layer. The layer direction is declared and enforced. | Name the source-truth layer (possibly `src/data`) in the project ruleset so later audits can check it. | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/engine/pricing.js` `calculateTotal` -> `PricingResult` | YES — `provenance` string names subtotal and the injected fee rate | YES — `confidence: 1.0` (exact arithmetic on its inputs) | PARTIAL — only `weightsVersion`; not a declared lineage-bearing layer, so not required | NO — typedef only; adoption-gap advisory (P7 — Contracted outputs) | PARTIAL — throws on unsupported currency; a deterministic calculation has no null outcome to express | NO — none; adoption-gap advisory (P9 — Golden baseline + explain-the-drift) |
| `src/services/gateway.js` `submitPayment` -> `GatewayResponse` | YES — `stub:` provenance that wraps the engine's provenance | YES — `confidence: 0.0`, `dataStatus: "simulated"` | YES — declared bearer: source, recordCount, fieldNames, configVersion all present; input values held only as text in provenance, needs-review (P8 — State-first lineage) | NO — typedef only; adoption-gap advisory (P7 — Contracted outputs) | NO — `accepted` is always `true`; adoption-gap advisory (spine) | NO — none; adoption-gap advisory (P9 — Golden baseline + explain-the-drift) |
| `src/ui/checkout.js` `buildCheckoutDisplay` -> `CheckoutDisplay` | YES — passes the engine's `provenance` through | YES — passes the engine's `confidence` through | PARTIAL — passes `weightsVersion` through; not a declared lineage-bearing layer, so not required | NO — typedef only; adoption-gap advisory (P7 — Contracted outputs) | PARTIAL — presentation of the engine result; engine errors propagate | NO — none; adoption-gap advisory (P9 — Golden baseline + explain-the-drift) |
| `src/data/rates.js` `CURRENCY_SYMBOLS` / `SUPPORTED_CURRENCIES` | N/A — static reference data, not derived | N/A — static reference data, not derived | N/A — static constant, nothing to reproduce | NO — JSDoc type annotation only | N/A — constant lookup table | N/A — static data, not a derived output |

Coverage map:

| File | Coverage |
| ---- | -------- |
| `src/ui/checkout.js` | read |
| `src/services/gateway.js` | read |
| `src/engine/pricing.js` | read |
| `src/data/rates.js` | read |
| `config/priors.json` | read |
| `.plumb-line/enforcement.json` | read |
| `eslint-boundary.config.cjs` | read |
| `eslint-boundary.cjs` | read |
| `package.json` | read |
| `package-lock.json` | not-read (generated dependency lockfile) |

```
coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.
```

The boundary rules were read and compared with the declared direction, but ESLint was not run (no `node_modules` in the fixture). Coverage of P1 — Source-truth layer is `partial`: no source-truth layer was declared.

5 findings: 0 violations, 1 needs-review, 4 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

**Notes below the report:**

- The checker passed on the exact text above, which is saved as `<harness>/work/js-clean/report.txt`. The subagent harness blocked writing a `.md` file, so the temp file uses `.txt`. I did not modify the target directory.
- **Save question:** the skill asks whether to save the report as `plumb-line-audit.md`. No builder was present to answer, so I did not write it.
- **Next steps:** there are no violations, so I made no remediate handoff. The one `needs-review` item asks the owner whether the lineage should hold the actual input values. The adoption-gap advisories (contracts, baselines, reject path, naming the source-truth layer) are the parts the project could take on next. No builder was present, so nothing was invoked.

## Decisions needed
1. Does the declared lineage definition (source, record count, field names, config version) count as enough for `submitPayment`, or should the actual input values (`subtotal`, `currency`) be stored as lineage fields? Recommendation: add them. It is two fields, and it makes the charge reproducible without parsing the provenance text.