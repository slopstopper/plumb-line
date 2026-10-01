report-format: v4
scope:               ./fixture (repository)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

## Principle glossary

```
P1 — Source-truth layer        P5 — Injectable priors     P8 — State-first lineage
P2 — One-way layering          P6 — Maturity vocabulary   P9 — Golden baseline + explain-the-drift
P3 — Confidence + provenance   P7 — Contracted outputs
spine — null-result expressibility
```

## Declared architecture (supplied in the invocation)

- Layer direction: ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed (so `ui -> engine` is legal). Enforced by `eslint-boundary.cjs`, which covers all six upward pairs (P2 — One-way layering). No layering violations found: `ui/checkout.js -> engine`, `services/gateway.js -> engine`, `engine/pricing.js -> data`.
- Priors: from `config/` (P5 — Injectable priors). `config/priors.json` is versioned (`1.0.0`), and the engine reads `processingFeeRate` only from injected config.
- Lineage-bearing output: the services layer. Its result must record source identity, record count, field names and config/version (P8 — State-first lineage).
- All outputs carry provenance and confidence and propagate the priors version (P3 — Confidence + provenance).
- Not declared: which layer is the source-truth layer (P1 — Source-truth layer). None was inferred, so coverage of P1 — Source-truth layer is `partial`.

## Findings

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/services/gateway.js` | 44-49 | `submitPayment` | needs-review | The lineage records source, `recordCount`, `fieldNames` and `configVersion`, so every declared key is present. But it does not record the input values (`subtotal`, `currency`) or when the call ran (`Date.now()` goes only into `transactionId`). `subtotal` can be recovered only by parsing the free-text `provenance` string. Whether this output can actually be reproduced from its lineage depends on whether the owner counts input values as "inputs needed to reproduce it". | Add the structured input values (and a timestamp) to `lineage`, or confirm with the owner that the four declared keys are enough. | P8 — State-first lineage |
| `src/engine/pricing.js` | 50 | `calculateTotal` | needs-review | `confidence: 1.0` is a literal. It is not derived from the confidence of the input `subtotal`, which comes in as a bare number with no provenance. The `provenance` string records how the fee was computed but not where `subtotal` came from, so any uncertainty in the input comes out as full certainty. | Take input provenance and confidence (or require the caller to state them) and derive the output confidence from them, or document that `subtotal` is always measured ground truth. | P3 — Confidence + provenance |
| `config/priors.json` | — | — | needs-review | The declared rule is that priors come from `config/`, but no module in scope loads `config/priors.json`, and there is no composition root. `calculateTotal` accepts any `config` object from its caller, so nothing ensures that the versioned priors file is what actually gets injected. | Add a named composition root or loader that reads `config/priors.json` and passes it in, and have the engine validate that `config.version` is present. | P5 — Injectable priors |
| `src/services/gateway.js` | 51-61 | `submitPayment` | advisory | `accepted: true` is hardcoded, so the stub cannot return a rejection or an inconclusive result. Rejection is neither declared nor practised elsewhere (the engine throws on an unsupported currency, which is an error rather than a rejection outcome), so this is an adoption gap, not a violation. The stub is labelled (`dataStatus: "simulated"`, `confidence: 0.0`, `stub-` transactionId). | When a real gateway is wired in, make the response able to express `accepted: false` or inconclusive. Meanwhile consider `accepted: null` for "not confirmed" instead of `true`. | spine — null-result expressibility |
| `src/services/gateway.js` | 32-62 | `submitPayment` | advisory | The simulated response is labelled but sits on the only payment path, with no explicit opt-in. A caller that ignores `dataStatus` sees `accepted: true` and a charged amount. The module header describes it as the "fetch/persist boundary" without a maturity term. | Mark the module `mock` in the maturity vocabulary, and gate simulated responses behind an explicit opt-in flag so they cannot reach a real consumer by default. | P6 — Maturity vocabulary |
| `src/` (all outputs) | — | — | advisory | Adoption gap. No public output has a versioned, validated contract (no version constant, validator or canonical key list; JSDoc typedefs only). Contracts are neither declared nor practised, so this is reported once. | Add a version constant, validator and key list for `GatewayResponse` first (the declared lineage-bearing output), then for `PricingResult` and `CheckoutDisplay`. | P7 — Contracted outputs |
| `fixture/` | — | — | advisory | Adoption gap. There are no tests and no golden baselines, so no derived output (fee, total, charge) is pinned against drift. Not declared or practised, so reported once. | Pin `calculateTotal` outputs for a fixed priors version in a golden baseline, and require an explanation whenever they change. | P9 — Golden baseline + explain-the-drift |
| `fixture/` | — | — | advisory | The source-truth layer is not explicitly declared (the direction ends at `data`, but no layer is named as measured or ground truth). So this audit's P1 — Source-truth layer coverage is partial. `src/data/rates.js` holds only static symbol mappings, and nothing derived was found in it. | Declare the source-truth layer in a ruleset file (`AGENTS.md` or `CLAUDE.md`), for example through the declaration-only entry of `plumb-line-bootstrap`. | P6 — Maturity vocabulary |

## Omission pass

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `calculateTotal` -> `PricingResult` (`src/engine/pricing.js`) | yes: formula string, but no origin for `subtotal` | literal `1.0`, not derived from inputs (needs-review) | not declared bearer; `weightsVersion` propagated | NO: typedef only (advisory gap) | throws on unsupported currency; no null outcome | NO (advisory gap) |
| `submitPayment` -> `GatewayResponse` (`src/services/gateway.js`) | yes: "stub: …" plus engine provenance | yes: `0.0` for a stub | yes: source, recordCount, fieldNames, configVersion; input values absent (needs-review) | NO: typedef only (advisory gap) | NO: `accepted` always `true` (advisory, rejection adopted nowhere) | NO (advisory gap) |
| `buildCheckoutDisplay` -> `CheckoutDisplay` (`src/ui/checkout.js`) | yes: passed through from engine | yes: passed through from engine | not declared bearer; `weightsVersion` propagated | NO: typedef only (advisory gap) | inherits engine throw; no null outcome | NO (advisory gap) |

## Coverage map

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
| `package-lock.json` | not-read (generated dependency lockfile) |

```
coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.
Coverage of P1 — Source-truth layer is partial because no source-truth layer was declared. The ESLint boundary rule was
read, not executed. git was unavailable in the sandbox, so the commit could not be resolved.
```

8 findings: 0 violations, 3 needs-review, 5 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

There are no confirmed violations. The service output does record every lineage field you declared (source, record count, field names, config version), and the layering follows the declared direction. Three things need your judgement:

- **Lineage:** the gateway's lineage doesn't record the actual input values, so the charge can't be fully reproduced from it.
- **Confidence:** the engine always reports confidence 1.0, whatever the input.
- **Priors:** nothing in the code loads `config/priors.json`, so there's no check that the versioned priors are what actually gets passed in.

Should I save this report to `plumb-line-audit.md`? After that, I can start `plumb-line-remediate` to work through the findings, or plan the fixes first.