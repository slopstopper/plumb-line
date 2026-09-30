report-format: v4
scope:               fixture/ (repository: src/, config/, boundary enforcement)
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P2 — One-way layering        P5 — Injectable priors    P7 — Contracted outputs
P3 — Confidence + provenance P6 — Maturity vocabulary  P8 — State-first lineage
P1 — Source-truth layer      P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied in the invocation): layers ui -> services -> engine -> data, one-way, non-adjacent downward skips allowed; priors from config/; services is the declared lineage-bearing output (source identity, record count, field names, config/version); outputs carry provenance + confidence and propagate the priors version. No source-truth layer was named and no composition root was declared, so P1 — Source-truth layer coverage is partial. Imports checked: ui -> engine (allowed skip), services -> engine, engine -> data; no upward import found, and `eslint-boundary.cjs` encodes the declared direction (P2 — One-way layering).

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ---- | ----- | ------------- | --------- |
| `src/services/gateway.js` | 44-49 | `submitPayment` | needs-review | Lineage has the four declared keys, but does not record the input `subtotal` (it appears nowhere in the response). `fieldNames` lists the engine result's output keys, not the input fields. `source` names a function, not a data source. `configVersion` is a caller-supplied string that is never checked against the fee rate actually used. The charge may not be reproducible from the lineage alone | Record the input values (`subtotal`, `currency`) and the applied `processingFeeRate` (or a hash of the config) in `lineage`, and confirm with the owner what "source identity" must name | P8 — State-first lineage |
| `src/services/gateway.js` | 52 | `submitPayment` | advisory | The stub can only return `accepted: true`, so it cannot express a declined or inconclusive payment. Rejection is neither declared nor practiced elsewhere, so this is an adoption gap, not a violation | Add a reject/inconclusive outcome to `GatewayResponse` (e.g. `accepted: false` with a reason) before a real gateway is wired | spine — null-result expressibility |
| `src/engine/pricing.js` | 35-51 | `calculateTotal` | advisory | Nothing loads `config/priors.json`. `config` is injected with no shape validation, so a missing `processingFeeRate` gives `NaN`, and `config.version` is never checked against the priors file. "Priors come from config/" is followed only by convention | Add a single config loader (a named composition root) that reads and validates `config/priors.json` and passes it down | P5 — Injectable priors |
| — | — | — | advisory | Contracts are adopted nowhere: output shapes have JSDoc typedefs only, with no version constant, validator or canonical key list | Add a version constant, validator and key list for `GatewayResponse` (the declared lineage-bearing output) first | P7 — Contracted outputs |
| — | — | — | advisory | Golden baselines are adopted nowhere: the fixture has no tests or pinned outputs, so drift in `processingFeeRate` or pricing would go unseen | Pin `calculateTotal`/`submitPayment` outputs for fixed inputs + priors version in a baseline test | P9 — Golden baseline + explain-the-drift |
| — | — | — | advisory | The declared architecture exists only in the invocation: the repo has no ruleset file (`AGENTS.md`/`CLAUDE.md`), and no source-truth layer or composition root is named (P1 — Source-truth layer) | Record the architecture in a ruleset file (the declaration-only entry of plumb-line-bootstrap), naming the source-truth layer | P6 — Maturity vocabulary |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `src/engine/pricing.js` `calculateTotal` -> `PricingResult` | yes — formula string with fee rate | yes — fixed `1.0` | partial — `weightsVersion` only; not the declared bearer | NO — JSDoc typedef only; adopted nowhere (advisory) | partial — throws on unsupported currency; no null outcome in the result | NO — adopted nowhere (advisory) |
| `src/services/gateway.js` `submitPayment` -> `GatewayResponse` | yes — `stub:` label nesting engine provenance, `dataStatus: "simulated"` | yes — `0.0` (stub, no confirmation) | PARTIAL — the four declared keys are present, but the input `subtotal` and the applied fee rate are not recorded (needs-review) | NO — JSDoc typedef only; adopted nowhere (advisory) | NO — `accepted` is always `true` (advisory adoption gap) | NO — adopted nowhere (advisory) |
| `src/ui/checkout.js` `buildCheckoutDisplay` -> `CheckoutDisplay` | yes — passed through from engine | yes — passed through from engine | partial — `weightsVersion` propagated; not the declared bearer | NO — JSDoc typedef only; adopted nowhere (advisory) | n/a — display of engine result; engine errors propagate | NO — adopted nowhere (advisory) |

| File | Coverage |
| ---- | -------- |
| `src/ui/checkout.js` | read |
| `src/services/gateway.js` | read |
| `src/engine/pricing.js` | read |
| `src/data/rates.js` | read |
| `config/priors.json` | read |
| `eslint-boundary.cjs` | read |
| `eslint-boundary.config.cjs` | read |
| `.plumb-line/enforcement.json` | read |
| `package.json` | read |
| `package-lock.json` | not-read (dependency lockfile, no source logic) |

```
coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness. The boundary
lint was read, not executed; git was unavailable in the sandbox, so commit is
reported from the session's git status (no commits, fixture untracked).
```

6 findings: 0 violations, 1 needs-review, 5 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

The audit found no confirmed violations. The one item to check is whether the service's lineage is enough to reproduce a charge: the input subtotal and the fee rate actually used are not recorded. The other five are advisory gaps.

Should I save this report to `fixture/plumb-line-audit.md`? I'll only write it if you say yes.

After that, I can run `plumb-line-remediate` on these findings, starting with the lineage item. I can also run `plumb-line-bootstrap` in declaration-only mode. It would write your architecture into a ruleset file, naming the source-truth layer, so the next audit doesn't depend on the prompt. Should I do either?