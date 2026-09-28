---
type: llm
focus: last_message
criteria: >-
  The report lists all three planted violations as confirmed violations,
  never as advisory or needs-review: (1) an upward import in data/rates.js
  (P2, one-way layering); (2) a hardcoded fee constant in engine/pricing.js
  (P5, injectable priors); (3) the gateway/service response missing
  provenance and confidence (P3). Only these three decide the verdict:
  other findings, whether advisory, needs-review or extra confirmed
  violations, are acceptable, because the fixture has more defects than the
  planted three. A missed planted violation, or one downgraded to advisory
  or needs-review, fails.
---
