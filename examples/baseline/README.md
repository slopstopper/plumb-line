# Worked baseline

A committed Principle 9 record. `baselines/fx-rate.json` pins `0.04 * 1.03`
with its lineage (two `real`/`high` inputs). Both `record.mjs` and
`record.py` recompute it and check against the pin; either language reads
the same file.

    node examples/baseline/record.mjs
    python3 examples/baseline/record.py
    node primitives/js/baseline-cli.mjs show fx-rate --dir examples/baseline/baselines

To see attribution, change `fx` to `source="fallback"` in either script and
run it: the report names `meta.lineage[1].source: "real" -> "fallback"`.
To accept a change, pass an explanation: `python3 examples/baseline/record.py "why"`.
