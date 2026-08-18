---
type: llm
focus: last_message
criteria: >-
  The report lists all three planted violations as confirmed violations,
  never as advisory or needs-review: (1) an upward import in data/schema.py
  (P2, one-way layering); (2) a hardcoded SIGNAL_THRESHOLD in
  engine/aggregate.py (P5, injectable priors); (3) services/source.py
  missing lineage (P8, state-first lineage). The P8 omission is the
  historical regression this suite guards: it is caught only by the
  omission pass, so it must appear as a violation, never downgraded.
  Extra advisory items are acceptable.
---
