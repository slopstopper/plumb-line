The audit found no confirmed violations: 8 findings, of which 3 need review and 5 are advisory. The code keeps to the declared layering, and the service layer records the four lineage keys you declared. The most important item is that the boundary lint gate is set up but couldn't run here: the installed ESLint fails to load, so nothing currently enforces the layer direction.

report-format: v4
scope:               ./fixture
principles-revision: 1
date:                2026-09-30
commit:              working tree (uncommitted)

```
P2 — One-way layering         P5 — Injectable priors      P8 — State-first lineage
P3 — Confidence + provenance  P6 — Maturity vocabulary    P9 — Golden baseline + explain-the-drift
P7 — Contracted outputs       spine — null-result expressibility
```

Declared architecture (supplied by the project owner in the invocation): one-way `ui -> services -> engine -> data`, non-adjacent downward skips allowed. Priors come from `config/`. `services` is the lineage-bearing output (source identity, record count, field names, config/version). Outputs carry provenance and confidence and propagate the priors version. No source-truth layer was named, so this audit does not infer one (see the advisory below).

Presence pass: every import points downward. `ui -> engine` is an allowed skip, `services -> engine`, `engine -> data`. `eslint-boundary.cjs` forbids all six upward pairs. The only fee rate comes from injected config. The service stub is labelled (`dataStatus: "simulated"`, `confidence: 0.0`, `stub-` transaction id, `stub:` provenance), so no fakery escapes. There are no tests and no baselines, so checks 6 and 10 have nothing to examine.

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `eslint-boundary.config.cjs` | — | — | needs-review | The boundary gate is configured but could not run. The installed ESLint 10.10.0 fails to load with a SyntaxError at `node_modules/eslint/lib/services/suppressions-service.js:58` (truncated source). The declared one-way rule is therefore unenforced in this tree. It may be only a local install problem. | Reinstall from the lockfile (`npm ci`), run the gate in pre-commit/CI, and confirm it rejects a test upward import such as engine importing services | P2 — One-way layering |
| `src/engine/pricing.js` | 50 | `calculateTotal` | needs-review | `confidence: 1.0` is a constant, even though the result depends on an injected judgment-call prior (`processingFeeRate`). A missing or malformed prior yields `NaN` fee/total and `weightsVersion: undefined` while still reporting full confidence. | Validate the config (rate present and numeric, version present) and throw or return an explicit inconclusive result on failure. Derive confidence rather than hard-set it, or document why arithmetic on a versioned prior is certain | P3 — Confidence + provenance |
| `src/engine/pricing.js` | 35–41 | `calculateTotal` | advisory | "Priors come from config/" is a caller convention, not a checked path. Nothing in `src/` loads `config/priors.json` (there is no composition root), and the engine accepts any object literal as `config`. | Add one loader/composition root that reads and validates `config/priors.json` and passes it down. Have callers take priors only from it | P5 — Injectable priors |
| `src/services/gateway.js` | 44–49 | `submitPayment` | needs-review | Lineage has the four declared keys, but it cannot regenerate the charge alone. `fieldNames` lists the engine's *output* keys, and the actual inputs (`subtotal`, `currency`) and the applied fee rate are recorded only inside the free-text `provenance` string. | Add the reproduction inputs to `lineage` as structured fields, e.g. `inputs: { subtotal, currency }` and `priors: { processingFeeRate }`, alongside `configVersion` | P8 — State-first lineage |
| `src/services/gateway.js` | 52 | `submitPayment` | advisory | Adoption gap: the stub can only return `accepted: true` and has no rejection or declined path. Rejection is neither declared nor practised anywhere, so this is not a violation. The stub is honestly labelled simulated. | When the real gateway lands, make `accepted: false` (declined/inconclusive) a reachable outcome with a reason field, and test it | spine — null-result expressibility |
| `src/services/gateway.js` | 10–21 | — | advisory | Adoption gap: no output shape (`PricingResult`, `GatewayResponse`, `CheckoutDisplay`) has a versioned, validated contract. They have JSDoc typedefs only: no validator, version constant or canonical key list. Contracts are adopted nowhere. | Add a schema version constant, a canonical key list and a validator per public shape, starting with `GatewayResponse` | P7 — Contracted outputs |
| `package.json` | — | — | advisory | Adoption gap: the project has no tests and no golden baselines, so no output is pinned and future drift would pass unseen. | Add golden-baseline tests for `calculateTotal`/`submitPayment` with a recorded reason required on any change | P9 — Golden baseline + explain-the-drift |
| `.plumb-line/enforcement.json` | — | — | advisory | The declared architecture exists only in this invocation. The repo has no ruleset file (`AGENTS.md`/`CLAUDE.md`) that records the layer direction, lineage-bearing layer or priors rule, and no source-truth layer is named. Coverage of source-truth checks is therefore partial. | Record the declaration in a ruleset file (e.g. via the bootstrap skill's declaration-only entry) and name the source-truth layer | P6 — Maturity vocabulary |

| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `engine/pricing.calculateTotal` -> `PricingResult` | yes: formula string with subtotal and fee rate | yes, but constant `1.0` (needs-review) | partial: `weightsVersion` only; not the declared bearer (P8 — State-first lineage) | NO: JSDoc typedef only (advisory, P7 — Contracted outputs) | partial: throws on unsupported currency; no inconclusive result for a bad prior | NO (advisory, P9 — Golden baseline + explain-the-drift) |
| `services/gateway.submitPayment` -> `GatewayResponse` | yes: `stub:` string plus `dataStatus: "simulated"` | yes: `0.0` for the stub | yes: source, recordCount, fieldNames, configVersion; inputs only in free text (needs-review, P8 — State-first lineage) | NO: JSDoc typedef only (advisory, P7 — Contracted outputs) | NO: always `accepted: true` (advisory, spine — null-result expressibility) | NO (advisory, P9 — Golden baseline + explain-the-drift) |
| `ui/checkout.buildCheckoutDisplay` -> `CheckoutDisplay` | yes: passed through from engine | yes: passed through from engine | partial: `weightsVersion` propagated; not the declared bearer (P8 — State-first lineage) | NO: JSDoc typedef only (advisory, P7 — Contracted outputs) | inherits engine behaviour (throws on unsupported currency) | NO (advisory, P9 — Golden baseline + explain-the-drift) |

```
read      src/data/rates.js
read      src/engine/pricing.js
read      src/services/gateway.js
read      src/ui/checkout.js
read      config/priors.json
read      eslint-boundary.cjs
read      eslint-boundary.config.cjs
read      .plumb-line/enforcement.json
read      package.json
not-read  package-lock.json
not-read  node_modules/ (third-party; out of scope; one file inspected only to diagnose the gate failure)
```

```
coverage: 9/10 files read, 0 partial, 1 not-read (90%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.
```

format-validation: scripts/check_report_format.py v6 — clean

8 findings: 0 violations, 3 needs-review, 5 advisory

---

- **Checker:** `check_report_format.py` v6 passed on this exact text.
- **Git:** git couldn't run in the sandbox, so the commit is recorded as the uncommitted working tree.
- **Gate test:** to check the boundary gate, I ran ESLint on a copy in `$TMPDIR` with a planted upward import. It failed with the same load error before any linting happened. Nothing in `./fixture` was changed.

Should I save this report to `fixture/plumb-line-audit.md`? After that, I can hand the findings to `plumb-line-remediate` to make the fixes, or run `plumb-line-bootstrap` to write the declared architecture into a ruleset file and wire up the gate.
