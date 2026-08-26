# Incident reconstruction — the retraction that started as a sign flip

> The full postmortem write-up for this reconstruction is at
> [`docs/postmortems/signflip.md`](../../docs/postmortems/signflip.md).

**This is a reconstruction modeling a failure class, not any lab's actual
code.** The class: an unversioned processing step quietly transforms data on
its way to a conclusion, and the stored conclusion records nothing about which
code produced it — so a wrong result is undetectable from the artifacts and
unattributable even after it is suspected. The documented public instance is
the 2006 retraction of five protein-structure papers (three in *Science*)
from Geoffrey Chang's lab: an inherited, homemade data-processing script
flipped two columns of crystallography data, inverting the derived
structures; the error stood for years and was found only when a contradicting
dataset forced a full re-derivation. See
["A Scientist's Nightmare: Software Problem Leads to Five Retractions"](https://www.science.org/doi/full/10.1126/science.314.5807.1856).
The data, pipeline, and conclusions below are synthetic.

## The demo

Two variants of a three-stage analysis (raw measurements → calibration →
conclusion), run twice each: once with the original calibration and once with
an "inherited" version whose operands are reversed — the sign flip.

**Broken** — no provenance. Two runs, two contradictory conclusions, stored
in identical format with no record of which processing produced which:

```sh
python3 broken/pipeline.py
```

**Instrumented** — every stage is `derive`d through the envelope, with a
`basis` label naming the exact code and version; each conclusion keeps its
chain:

```sh
python3 instrumented/pipeline.py
```

The conclusions still contradict each other — provenance does not fix a
flipped sign. What changes is that each stored conclusion can answer *which
data, through which code, produced this number*, so the flip is attributable
in one read instead of after a full re-derivation. The final section shows
the incident's storage habit directly: a conclusion kept as `derived` with no
lineage is flagged by `audit_meta` as `unreproducible` — a claim that cannot
be audited.

## Scope

A minimal shape-demonstrator (~40 and ~80 lines): no real instrument, no
notebook, no dependencies beyond the Python standard library and the in-repo
primitive (imported via its flat-usage shim). The integrity test
(`test_pipeline_demo.py`) runs both scripts and locks the behavioral
markers — broken stores indistinguishable contradictions, instrumented
attributes each conclusion, the bare conclusion is flagged.
