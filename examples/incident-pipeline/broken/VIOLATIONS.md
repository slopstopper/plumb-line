# Answer key — planted violations in `broken/pipeline.py`

This variant is the reconstruction's *incident state*: the violations are the
point, and an audit of this directory should find them, not treat them as
regressions. See `../README.md` for the incident being modeled.

| ID | Where | Violation |
| --- | --- | --- |
| P8 | `conclude`, `main` | Missing lineage — conclusions are stored with no record of the inputs, code, or versions that produced them; the two contradictory results are unattributable from the artifacts |
| P5 | `BASELINE`, `calibrate_*` | Hardcoded prior — the calibration baseline is a judgment call buried as a module constant, and the calibration convention itself (which operand is subtracted) is invisible logic rather than a named, versioned step |
| P9 | `main` | Unexplained drift — the second run's conclusion flips the first with nothing forcing an explanation; no baseline pins the derived output, so the change surfaces as silence |

The `instrumented/` variant resolves the P8 finding via the provenance
primitive (each stage derives with a `basis` naming code+version, and each
conclusion keeps its chain). The P5 baseline stays a constant in both
variants, and P9 (a pinned golden baseline) is deliberately not adopted —
each would be a next step in a real adoption, not shown here.
