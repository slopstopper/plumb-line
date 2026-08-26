# Answer key — planted violations in `broken/loadsheet.py`

This variant is the reconstruction's *incident state*: the violations are the
point, and an audit of this directory should find them, not treat them as
regressions. See `../README.md` for the incident being modeled.

| ID | Where | Violation |
| --- | --- | --- |
| P5 | `STANDARD_WEIGHT_KG`, `TITLE_CATEGORY` | Hardcoded priors — the standard weights and the honorific→category convention are judgment calls buried as module constants, invisible to every consumer of the total and changeable only by editing logic |
| P3 | `categorize`, `main` | No provenance or confidence — a category guessed from a title is indistinguishable from one read from the booking record, and the total carries no signal that any input was inferred |
| P1 | `main` | Inferred values enter the calculation stream mixed with recorded ones — the guessed category sits in the same data path as booked ground truth with nothing separating them |

The `instrumented/` variant resolves the P3/P1 findings via the provenance
primitive (guesses are labeled `inferred` and the total inherits their
uncertainty). The P5 priors are deliberately left as constants in both
variants — lifting them to injected, versioned config is the next step in a
real adoption, not shown here.
