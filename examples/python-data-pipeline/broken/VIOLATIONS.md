# Planted Violations — Answer Key

This file is the answer key for the audit of `broken/`. There are exactly three violations.

---

## P2 — Boundary leak (upward import)

**File:** `src/data/schema.py`

**What is wrong:** The `data` layer imports from `src.ui.report`. Data is the bottom layer; it must not import anything from a layer above it. Imports must flow one way only: `ui → services → engine → data`.

---

## P5 — Hardcoded prior

**File:** `src/engine/aggregate.py`

**What is wrong:** The file declares `SIGNAL_THRESHOLD = 0.65` as a module-level constant and uses it directly (`threshold = SIGNAL_THRESHOLD`) instead of reading the threshold from the injected `config` argument. All weights and priors must come through the injected config so they are visible, versioned, and overridable — never baked into the module body.

---

## P8 — Missing lineage

**File:** `src/services/source.py`

**What is wrong:** `load_and_aggregate` returns a computed result without recording the inputs needed to reproduce it. The `lineage` field is absent. A caller cannot determine which source was used, how many records were loaded, which field names were present, or which config version drove the aggregation. Clean practice records these inputs so every output can be traced back to the conditions that produced it.
