# Planted Violations — Answer Key

This file is the answer key for the audit of `broken/`. There are exactly three violations.

---

## P2 — Boundary leak (upward import)

**File:** `src/data/rates.js`

**What is wrong:** The `data` layer imports from `../ui/checkout.js`. Data is the bottom layer; it must not import anything from a layer above it. Imports must flow one way only: `ui → engine → services → data`.

---

## P5 — Hardcoded prior

**File:** `src/engine/pricing.js`

**What is wrong:** The file declares `const FEE = 0.029` and uses it directly instead of reading the fee rate from the injected `config` argument. All weights and priors must come through the injected config so they are visible, versioned, and overridable — never baked into the function body.

---

## P3 — Laundered data (missing provenance and confidence)

**File:** `src/services/gateway.js`

**What is wrong:** `submitPayment` returns a hardcoded mock amount (`MOCK_CHARGED_AMOUNT = 42.00`) with no `provenance` or `confidence` fields on the response object. A caller has no way to know the value is simulated. Mock or stub data must be explicitly labelled with provenance and a confidence score so uncertainty is never hidden from downstream logic.
