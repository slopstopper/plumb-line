report-format: v4
scope:               src/
principles-revision: 1
date:                2026-09-30
commit:              no repository (not version-controlled)

P2 — One-way layering  P3 — Confidence + provenance  P5 — Injectable priors

| Path | Line | Function | Status | Issue | Suggested Fix | Principle |
| ---- | ---- | -------- | ------ | ----- | ------------- | --------- |
| `src/data/rates.js` | 7 | — | violation | the data layer imports from the ui layer, against the declared one-way direction | remove the upward dependency so the data layer depends on nothing above it | P2 — One-way layering |
| `src/engine/pricing.js` | 9, 42 | `calculateTotal` | violation | the processing fee is a hardcoded constant rather than a prior from config | read the fee from the injected config instead of a module constant | P5 — Injectable priors |
| `src/services/gateway.js` | 15 | `submitPayment` | violation | a mock payment result is returned with no provenance or confidence, so it reads as real | label the output with its true provenance and a confidence it can support | P3 — Confidence + provenance |

| Output | Provenance | Confidence | Lineage | Contract | Null-expressible | Baseline |
| ------ | ---------- | ---------- | ------- | -------- | ---------------- | -------- |
| `submitPayment` | NO — mock result unlabelled (P3 — Confidence + provenance) | NO | no | no | yes | no |

coverage: 3/9 files read, 0 partial, 6 not-read (33%)
scope note: findings are drawn from the read set only; a not-read file with no
finding is not a clean file. This audit does not claim completeness.

3 findings: 3 violations, 0 needs-review, 0 advisory
