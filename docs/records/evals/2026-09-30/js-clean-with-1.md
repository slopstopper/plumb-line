report-format: v4
scope:               ./fixture (repository; node_modules and package-lock.json excluded as third-party/generated)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

**Principle glossary**

```
P2 — One-way layering        P5 — Injectable priors    P7 — Contracted outputs
P3 — Confidence + provenance P6 — Maturity vocabulary  P8 — State-first lineage
P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

**Declared architecture (supplied by the project owner in the invocation):** layer direction ui -> services -> engine -> data, with downward skips allowed (P2 — One-way layering); priors come from `config/` (P5 — Injectable priors); the services layer is the lineage-bearing output and must record source identity, record count, field names and config/version (P8 — State-first lineage); outputs carry provenance and confidence and pass the priors version along (P3 — Confidence + provenance).

**Findings**

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `fixture/src/engine/pricing.js` | 40–51 | `calculateTotal` | needs-review | The injected config is never checked. If `processingFeeRate` or `version` is missing, `fee`/`total` become `NaN` while `confidence` stays a hardcoded `1.0`, and `weightsVersion` (and so the service's `lineage.configVersion`) becomes `undefined`. A missing prior then reads as a certain result. Nothing in the repo loads `config/priors.json`, so it can't be confirmed from here whether callers always pass a well-formed prior. | Validate the config shape (numeric rate, non-empty version) at the engine boundary. Reject or lower confidence when a prior is missing, and add a loader for `config/priors.json` so the config/ source is enforced, not only documented. | P3 — Confidence + provenance |
| `fixture/src/services/gateway.js` | 51–61 | `submitPayment` | advisory | `accepted` is typed `boolean` but can only be `true`, so the stub can't express a declined or inconclusive payment. Rejection is neither declared in the architecture nor practised as an outcome by sibling code (the engine only throws on unsupported currency, which is input validation). So this is an adoption gap, not a violation. The stub is honestly labelled (`dataStatus: "simulated"`, `confidence: 0.0`, `stub-` transaction id). | Before a real gateway replaces the stub, add a reject/inconclusive path (`accepted: false` with a reason) and a test that exercises it. | spine — null-result expressibility |
| `fixture/src/` | — | — | advisory | No output shape has a versioned, validated contract. There are JSDoc typedefs only, with no validator, no contract version constant and no canonical key list. Contracts are neither declared nor practised anywhere, so this is one adoption gap. | Once `GatewayResponse` is consumed downstream, give it a versioned contract (version constant + key list + validator), starting with the lineage-bearing services output. | P7 — Contracted outputs |
| `fixture/` | — | — | advisory | There are no tests and no golden baselines, so nothing pins the pricing arithmetic or the gateway output shape, and drift would go unseen. Adopted nowhere, so this is one adoption gap. | Add a golden baseline for `calculateTotal` and `submitPayment` (fixed inputs and priors version), with a recorded reason whenever it changes. | P9 — Golden baseline + explain-the-drift |
| `fixture/package.json` | 1–2 | — | advisory | The boundary rules in `eslint-boundary.cjs` are correct and complete (all six upward pairs are forbidden), but no script, hook or CI runs them. The installed ESLint 10.10.0 also crashes on load (`SyntaxError` in `node_modules/eslint/lib/services/suppressions-service.js`), so the gate can't currently execute. The one-way layering holds today only because a manual read found it holds. | Add a `lint:boundary` script and a pre-commit/CI hook, and repair the ESLint install so the gate actually runs. | P2 — One-way layering |
| `fixture/` | — | — | advisory | The declared architecture (layer direction, priors in config/, services as the lineage-bearing layer) came only from the invocation. No ruleset file (`AGENTS.md`, `CLAUDE.md`) records it in the repo, so the next audit or contributor can't recover it. | Record the declaration in a ruleset file, e.g. via the declaration-only entry of plumb-line-bootstrap. | P6 — Maturity vocabulary |

**Omission pass**

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `engine/pricing.js` `calculateTotal` → `PricingResult` | YES — derivation string with subtotal and fee rate | YES — hardcoded `1.0`, not lowered when a prior is missing (see finding) | NOT REQUIRED — engine is not the declared bearer; `weightsVersion` is propagated | NO — JSDoc only (adoption gap) | PARTIAL — throws on unsupported currency; no "no result" outcome otherwise | NO — none (adoption gap) |
| `services/gateway.js` `submitPayment` → `GatewayResponse` | YES — `stub:` provenance wrapping engine provenance, plus `dataStatus: "simulated"` | YES — `0.0` for an unconfirmed stub | YES — declared bearer; `lineage` records source, `recordCount`, `fieldNames`, `configVersion`; `weightsVersion` propagated | NO — JSDoc only (adoption gap) | NO — `accepted` is always `true` (advisory, adoption gap) | NO — none (adoption gap) |
| `ui/checkout.js` `buildCheckoutDisplay` → `CheckoutDisplay` | YES — engine provenance passed through | YES — engine confidence passed through | NOT REQUIRED — not the declared bearer; `weightsVersion` propagated | NO — JSDoc only (adoption gap) | NO — inherits engine throw only | NO — none (adoption gap) |
| `data/rates.js` `CURRENCY_SYMBOLS` / `SUPPORTED_CURRENCIES` | N/A — static source-truth constants | N/A — static reference data | N/A — source-truth layer | NO — no contract (adoption gap) | N/A — static data | NO — none (adoption gap) |

**Coverage map**

| File | Status |
| ---- | ------ |
| `fixture/src/data/rates.js` | read |
| `fixture/src/engine/pricing.js` | read |
| `fixture/src/services/gateway.js` | read |
| `fixture/src/ui/checkout.js` | read |
| `fixture/config/priors.json` | read |
| `fixture/eslint-boundary.cjs` | read |
| `fixture/eslint-boundary.config.cjs` | read |
| `fixture/.plumb-line/enforcement.json` | read |
| `fixture/package.json` | read |
| `fixture/package-lock.json` | not-read (generated lockfile) |
| `fixture/node_modules/` | not-read (third-party dependencies, out of scope) |

```
coverage: 9/10 in-scope files read, 0 partial, 1 not-read (90%); node_modules/ excluded from the denominator
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.
The boundary lint could not be executed (the installed ESLint crashes on load); layering was checked by manual reading of every import.
```

format-validation: scripts/check_report_format.py v6 — clean

6 findings: 0 violations, 1 needs-review, 5 advisory

---

The fixture meets every rule you declared: imports only go down the layers, the fee rate comes in as a prior, and outputs carry provenance, confidence and the priors version. The service output records all four lineage fields (source, record count, field names, config version).

- **The one open item** is the needs-review finding: the engine never checks its config. A missing prior would produce a `NaN` total that still reports confidence `1.0`.
- **The five advisories** are gaps in things the project hasn't taken on yet: there's no reject path in the payment stub, no output contracts, no golden baselines, the boundary lint isn't run by anything (and the installed ESLint crashes), and the architecture isn't written into a ruleset file in the repo.

Two questions:
1. Should I save this report to `plumb-line-audit.md`?
2. Next step: I can hand these findings to `plumb-line-remediate` to make the fixes, or to `plumb-line-bootstrap` to connect the boundary lint to a script and pre-commit hook and write the architecture into a ruleset file. Or I can stop here.
