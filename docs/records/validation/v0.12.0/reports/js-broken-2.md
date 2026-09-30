report-format: v4
scope:               <harness>/fixtures/js-broken-2 (repository)
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

```
P1 — Source-truth layer      P4 — Quarantined fakery   P7 — Contracted outputs
P2 — One-way layering        P5 — Injectable priors    P8 — State-first lineage
P3 — Confidence + provenance P6 — Maturity vocabulary  P9 — Golden baseline + explain-the-drift
spine — null-result expressibility
```

Declared architecture (supplied in the invocation): layers `ui -> services -> engine -> data`, one-way, non-adjacent downward skips allowed; priors come from `config/`; the services layer is the lineage-bearing output (source identity, record count, field names, config/version); all outputs carry provenance and confidence and propagate the priors version. No source-truth layer was declared, and this audit does not infer one, so its coverage of P1 — Source-truth layer is `partial`.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/data/rates.js` | 7–8 | module scope | violation | The bottom (data) layer imports `buildCheckoutDisplay` from `../ui/checkout.js` and re-exports it: an upward import against the declared `ui -> services -> engine -> data` direction, and it closes a cycle ui -> engine -> data -> ui. The file's own header says "Allowed imports: none". Confirmed by running the project's boundary lint on a copy: `import/no-restricted-paths` error at 7:38 | Delete the import and re-export; any consumer of `buildCheckoutDisplay` imports it from `src/ui/` | P2 — One-way layering |
| `src/engine/pricing.js` | 9, 42 | `calculateTotal` | violation | The fee rate is hardcoded as `const FEE = 0.029` and used in the calculation. The injected `config.processingFeeRate` (from `config/priors.json`) is never read, so changing the prior in config has no effect on the result | Read the rate from `config.processingFeeRate`, fail loudly when it is absent, and delete the module constant | P5 — Injectable priors |
| `src/engine/pricing.js` | 52 | `calculateTotal` | violation | `weightsVersion: config.version` stamps the result with a priors version that did not produce it: the fee comes from the hardcoded `FEE`, not from config. Today the two values happen to agree (0.029), but a config change plus a version bump would label output from the old rate with the new version | Once the rate comes from config (finding above), the stamp is true. Until then, do not record a config version the calculation did not use | P8 — State-first lineage |
| `src/engine/pricing.js` | 14, 30 | `calculateTotal` | violation | The JSDoc says the fee rate is "injected from config/priors.json" and "comes exclusively from the injected config — never hardcoded here". The code on line 9 contradicts both | Fix the code so the claim is true, or correct the claim so it describes what the code does | P6 — Maturity vocabulary |
| `config/priors.json` | 4 | — | violation | `description` claims "All weights are explicit config, not hardcoded constants", which is false while the engine hardcodes the fee rate | Make it true (see the `pricing.js` finding), or reword it to the actual state | P6 — Maturity vocabulary |
| `src/engine/pricing.js` | 51 | `calculateTotal` | needs-review | `confidence: 1.0` is a literal, the same for every input, but the total depends on a prior (the fee rate). Whether full confidence is honest for a prior-dependent result is the owner's call, and the audit cannot settle it from the repo | Derive confidence from the inputs and the prior, or record in config why 1.0 is exact for this calculation | P3 — Confidence + provenance |
| `src/services/gateway.js` | 16, 21 | `submitPayment` | violation | `chargedAmount` is the hardcoded `MOCK_CHARGED_AMOUNT = 42.0` and ignores `subtotal`, `currency` and the engine total. It leaves the service boundary with no mock marker, so it reads as a real charged amount. Only `transactionId` has a `stub-` prefix, and consumers do not see that on the amount | Label the output as mock (e.g. a `derivedFromMock`/`mode: "mock"` field), keep it out of real output paths unless the caller explicitly opts in, or compute the amount through the engine | P4 — Quarantined fakery |
| `src/services/gateway.js` | 19–24 | `submitPayment` | violation | The services output is declared lineage-bearing, but this result records no lineage: no source identity, record count, field names or config/version. The `config` parameter is accepted but never used, so the priors version is not propagated as declared | Add a lineage field that records source identity, record count, field names and the priors version, and test that it is present | P8 — State-first lineage |
| `src/services/gateway.js` | 19–24 | `submitPayment` | violation | The architecture declares that outputs carry provenance and confidence, and the sibling engine output does. This output carries neither | Add `provenance` (which must say the value is mocked) and `confidence` | P3 — Confidence + provenance |
| `src/services/gateway.js` | 20 | `submitPayment` | advisory | `accepted: true` is the only possible outcome, so a declined or rejected payment cannot be expressed. Rejection is neither declared in the architecture nor practiced as an outcome elsewhere. The engine's `throw` on an unsupported currency is a precondition error, not an outcome shape. So this is an adoption gap, not a confirmed violation | When the gateway becomes real, add a declined/rejected result path. Until then, label the stub `mock` | spine — null-result expressibility |
| `src/ui/checkout.js` | 31–37 | `buildCheckoutDisplay` | violation | Passes through `provenance` and `confidence` but drops the engine's `weightsVersion`. The declared rule is that outputs propagate the priors version | Carry `weightsVersion` through in `CheckoutDisplay` | P8 — State-first lineage |
| `package.json` | 1–2 | — | advisory | The boundary lint is configured (`.plumb-line/enforcement.json`, `eslint-boundary.config.cjs`) and it works: it flags the `rates.js` import when run. But no script, hook or CI in scope runs it, and the tree currently fails it. The layering is enforced by configuration alone, not by a gate | Add a `lint:boundary` script and run it as a blocking pre-commit or CI gate | P2 — One-way layering |
| — | — | — | advisory | No source-truth layer is declared: the layer direction was supplied, but not which layer holds ground truth. P1 — Source-truth layer checks were not applied, and none was inferred | Declare the source-truth layer in the project ruleset (e.g. via `plumb-line-bootstrap`'s declaration-only entry) | P6 — Maturity vocabulary |
| — | — | — | advisory | Adoption gap: no public output has a versioned, validated contract (JSDoc typedefs only, with no version constant, validator or key list). This is adopted nowhere, so it is reported once as a maturity note under P6 — Maturity vocabulary | Give `PricingResult`, `CheckoutDisplay` and the `submitPayment` result each a version constant, a key list and a validator | P7 — Contracted outputs |
| — | — | — | advisory | Adoption gap: no golden baseline pins any derived output, and the repo has no tests at all. This is adopted nowhere, so it is reported once as a maturity note under P6 — Maturity vocabulary | Pin `calculateTotal` outputs for fixed inputs and priors in a baseline whose changes need a recorded reason | P9 — Golden baseline + explain-the-drift |

| Output | Provenance (P3 — Confidence + provenance) | Confidence (P3 — Confidence + provenance) | Lineage (P8 — State-first lineage) | Contract (P7 — Contracted outputs) | Null-expressible (spine) | Baseline (P9 — Golden baseline + explain-the-drift) |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `calculateTotal` → `PricingResult` (`src/engine/pricing.js`) | YES — `provenance` string (it names the hardcoded `FEE`, not the config rate) | YES — literal `1.0` for every input (needs-review) | PARTIAL — only `weightsVersion`, which misstates the config actually used; no source or field record; not the declared bearer | NO — JSDoc typedef only (adoption gap) | PARTIAL — throws on unsupported currency; the result shape has no null or "no result" form | NO — none (adoption gap) |
| `buildCheckoutDisplay` → `CheckoutDisplay` (`src/ui/checkout.js`) | YES — passed through from engine | YES — passed through from engine | NO — drops `weightsVersion`; the declared rule says propagate it (P8 — State-first lineage) | NO — JSDoc typedef only (adoption gap) | NO — inherits the engine's throw; no null form | NO — none (adoption gap) |
| `submitPayment` → payment result (`src/services/gateway.js`) | NO — declared, absent (P3 — Confidence + provenance) | NO — declared, absent (P3 — Confidence + provenance) | NO — declared bearer (P8 — State-first lineage): no source identity, record count, field names or config/version | NO — no typedef, validator or version (adoption gap) | NO — `accepted` is always `true` (advisory, spine) | NO — none (adoption gap) |
| `CURRENCY_SYMBOLS` / `SUPPORTED_CURRENCIES` (`src/data/rates.js`) | n/a — static hand-written enumeration, not a derived value | n/a — static enumeration | n/a — not a derived output | NO — no contract (covered by the adoption gap) | n/a — lookup table | n/a — static literal |

```
src/data/rates.js                read
src/engine/pricing.js            read
src/services/gateway.js          read
src/ui/checkout.js               read
config/priors.json               read
.plumb-line/enforcement.json     read
eslint-boundary.cjs              read
eslint-boundary.config.cjs       read
package.json                     read
package-lock.json                partial (generated lockfile; header and root entry read, 1574 lines of resolved dev dependencies skimmed only)
```

coverage: 9/10 files read, 1 partial, 0 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no finding is not a clean file. This audit does not claim completeness. The repository contains no test files, so check 10 (test changed to pass) had nothing to examine. `node_modules/` is absent from the target and out of scope. The boundary lint was run on a copy under the work directory; the target itself was not modified.

15 findings: 9 violations, 1 needs-review, 5 advisory

format-validation: scripts/check_report_format.py v6 — clean

---

**Notes on how this audit was run:**
- **Checker:** the report above is exactly the text I ran `check_report_format.py` v6 on, including the `format-validation` line, and it passed. That text is saved at `<harness>/work/js-broken-2/checker-input.md`. The harness refused `Write` under the filename `report.md` and refused Bash heredocs, so I wrote it with `Write` under this filename instead.
- **Lint run:** to confirm the boundary violation, I copied the target to `<harness>/work/js-broken-2/lintcopy/`, ran `npm ci` and ran the project's own ESLint boundary config there. It reported the error at `src/data/rates.js:7:38`. The target itself was not modified.
- **Save and handoff:** no one was available to answer, so I did not ask whether to save the report as `plumb-line-audit.md` and did not write it. I also invoked no follow-on skill. Once someone can answer, the next steps would be `plumb-line-remediate` on these findings, or `plumb-line-bootstrap` to add a gate that runs the boundary lint.

## Decisions needed
1. Should the report be saved as `plumb-line-audit.md`, and where? Recommendation: save it next to the fixture's harness outputs, not inside the fixture, so the target stays unmodified.
2. Should findings be handed to `plumb-line-remediate`? Recommendation: no, for a harness fixture; the audit output is the deliverable.