I found no violations, 3 findings that need review and 3 advisory gaps. The layering rules are met and a lint rule enforces them, so the gaps are elsewhere. The payment service's lineage has all four fields you asked for, but not the input values needed to reproduce a charge. The pricing engine reports confidence 1.0 even when its config is missing. Nothing in the code loads `config/priors.json`. `git` isn't available in the sandbox, so I couldn't check history and `commit` shows the working tree. The report format checker passes it.

report-format: v4
scope:               ./fixture (repository; node_modules/ excluded as third-party)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P1 — Source-truth layer      P5 — Injectable priors    P8 — State-first lineage
P2 — One-way layering        P5 — Injectable priors    P9 — Golden baseline + explain-the-drift
P3 — Confidence + provenance P7 — Contracted outputs
spine — null-result expressibility
```

Declared architecture (supplied by the owner in the invocation): layers ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors from `config/`; services is the lineage-bearing output (source identity, record count, field names, config/version); outputs carry provenance + confidence and propagate the priors version. Layer imports checked: `ui -> engine` (allowed skip), `services -> engine`, `engine -> data`. No upward import found; `eslint-boundary.cjs` forbids every upward edge, so P2 — One-way layering is clean and enforced.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/services/gateway.js` | 37, 44–49 | `submitPayment` | needs-review | Lineage carries the four declared keys, but not the input values needed to reproduce the charge: `subtotal` and `currency` are not recorded (`subtotal` isn't in the response at all), `transactionId` comes from an unrecorded `Date.now()`, and `source` names a function, not the source of the data | Record the call inputs (`subtotal`, `currency`) and the timestamp or seed behind `transactionId` in `lineage`; have the owner confirm whether "source identity" means the calling code or the origin of the data | P8 — State-first lineage |
| `src/engine/pricing.js` | 40–51 | `calculateTotal` | needs-review | The injected prior is never validated and `confidence` is the literal `1.0`. A missing or invalid `processingFeeRate` or `version` gives `NaN` totals and `weightsVersion: undefined`, still reported at confidence 1.0 | Validate `config` on entry (a finite rate, a version string) and return an explicit invalid or inconclusive result; set confidence from input validity instead of a constant | P3 — Confidence + provenance |
| `config/priors.json` | — | — | needs-review | Nothing in scope loads `config/priors.json`; `config` is supplied by callers outside the tree, so it cannot be shown that the priors used really come from `config/` rather than an inline literal | Add one loader (the composition root) that reads and validates `config/priors.json` and injects it, or point to the caller that does this | P5 — Injectable priors |
| `src/services/gateway.js` | 52 | `submitPayment` | advisory | `accepted: true` is unconditional, so the stub cannot express rejection or an inconclusive result, even though it reports `dataStatus: "simulated"` and confidence 0.0. No layer declares or practises a reject path, so this is an adoption gap, not a violation | Add a reject/inconclusive outcome (e.g. `accepted: false` or `null` with a reason) before a real gateway replaces the stub, or make `accepted` reflect `dataStatus` | spine — null-result expressibility |
| `src/` (all output shapes) | — | — | advisory | No output shape has a versioned, validated contract: `PricingResult`, `GatewayResponse` and `CheckoutDisplay` are JSDoc typedefs only, with no version constant, key list or validator. Neither declared nor practised, so reported once as an adoption gap | If contracts are adopted, add a version constant, a canonical key list and a validator per public shape, starting with `GatewayResponse` | P7 — Contracted outputs |
| `fixture/` | — | — | advisory | No tests and no golden baseline pin any output; drift in totals, fees or lineage would go unnoticed. Adopted nowhere, so reported once. The source-truth layer was also not named in the declaration (P1 — Source-truth layer), so that principle was not assessed | Add a baseline for `calculateTotal` / `submitPayment` against a pinned priors version; have the owner name the source-truth layer (possibly `data/`) | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine — null-result expressibility) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `calculateTotal` → `PricingResult` (`src/engine/pricing.js`) | YES — derivation string with the fee rate | PARTIAL — hardcoded `1.0`, not tied to input validity | PARTIAL — `weightsVersion` only; engine is not a declared bearer | NO — JSDoc only (adoption gap) | PARTIAL — throws on unsupported currency; no in-band null or invalid result | NO |
| `submitPayment` → `GatewayResponse` (`src/services/gateway.js`) | YES — stub-labelled, chains engine provenance | YES — `0.0` for the simulated amount, plus `dataStatus` | PARTIAL — the four declared keys are present, but the input values and `transactionId` seed are missing (declared bearer, P8 — State-first lineage) | NO — JSDoc only (adoption gap) | NO — `accepted` is always `true` | NO |
| `buildCheckoutDisplay` → `CheckoutDisplay` (`src/ui/checkout.js`) | YES — passed through from engine | YES — passed through from engine | PARTIAL — propagates `weightsVersion`; ui is not a declared bearer | NO — JSDoc only (adoption gap) | NO — inherits the engine throw; no display state for invalid/inconclusive | NO |

| File | Status |
| ---- | ------ |
| `src/ui/checkout.js` | read |
| `src/services/gateway.js` | read |
| `src/engine/pricing.js` | read |
| `src/data/rates.js` | read |
| `config/priors.json` | read |
| `eslint-boundary.cjs` | read |
| `eslint-boundary.config.cjs` | read |
| `.plumb-line/enforcement.json` | read |
| `package.json` | read |
| `package-lock.json` | not-read (generated lockfile) |
| `node_modules/` | excluded (third-party, outside the denominator) |

coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings come only from the files read; an unread file with no finding is not a clean file. This audit does not claim completeness. Git history could not be inspected (git is unavailable in the sandbox), so drift and history-based checks relied on the working tree only.

format-validation: scripts/check_report_format.py v6 — clean

6 findings: 0 violations, 3 needs-review, 3 advisory

---

Should I save this as `plumb-line-audit.md`? After that, I can either run `plumb-line-remediate` to apply the findings, or run `plumb-line-bootstrap` to add the missing config validation and the lineage and contract checks.
