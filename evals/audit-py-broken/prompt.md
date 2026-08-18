---
name: audit-py-broken
tags: [audit, blind-validation]
plugins: ["../.."]
runs: 3
max_turns: 40
timeout_seconds: 600
---

Audit the code in ./fixture against the plumb-line principles using the
plumb-line audit skill.

Declared architecture, supplied as the project owner would supply it: one-way
layer direction ui -> services -> engine -> data, non-adjacent downward skips
allowed; priors come from config/; the service layer is the lineage-bearing
output, meaning its result must record a lineage of the inputs needed to
reproduce it (source identity, record count, field names, config/version).
Outputs also carry provenance and confidence and propagate the priors version.

Produce the full audit report in your final message.
