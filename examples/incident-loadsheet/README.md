# Incident reconstruction — the plane that thought its passengers were children

> The full postmortem write-up for this reconstruction is at
> [`docs/postmortems/loadsheet.md`](../../docs/postmortems/loadsheet.md).

**This is a reconstruction modeling a failure class, not any airline's actual
code.** The class: a category guessed from a label enters a safety-relevant
calculation indistinguishable from a category that was actually known. The
documented public instance is the TUI Airways Boeing 737-8K5 (G-TAWG) serious
incident of 21 July 2020: after an IT system change, every adult female
passenger titled "Miss" was classified as a child and assigned the child
standard weight (35 kg instead of 69 kg), understating the load sheet by
1,244 kg — the software had been programmed where "Miss" denotes a child. See
the [AAIB investigation report](https://www.gov.uk/aaib-reports/aaib-investigation-to-boeing-737-8k5-g-tawg-21-july-2020).
The manifest, weights, and totals below are synthetic.

## The demo

Two variants of a ten-passenger load-sheet calculation where three categories
are guessed from honorifics. Same manifest, same arithmetic, same (wrong)
total — one difference.

**Broken** — no provenance. The sheet is tidy and confident:

```sh
python3 broken/loadsheet.py
```

**Instrumented** — each weight is `mark`ed with how its category was known:
`real/medium` when the category is a booking-record fact feeding an approved
standard-weight estimate, `inferred/low` when the category itself was guessed
from the honorific. No passenger is weighed, so no row claims high
confidence. The total is `derive`d under the combination law:

```sh
python3 instrumented/loadsheet.py
```

The instrumented total is the same number — provenance doesn't fix a wrong
guess — but its envelope carries `confidence: low`, `weakest_source: inferred`,
and the guessed fraction as a computed property of lineage (`3/10`). The final
section attempts the incident's exact move, issuing the sheet as fully
confident (`derive` with `confidence: "high"`): `audit_meta` flags the
over-claim, because the lineage says otherwise.

## Scope

A minimal shape-demonstrator (~50 and ~80 lines): no real check-in system, no
dependencies beyond the Python standard library and the in-repo primitive
(imported via its flat-usage shim). The integrity test
(`test_loadsheet_demo.py`) runs
both scripts and locks the behavioral markers — broken stays tidy and silent,
instrumented carries its uncertainty, the over-claim is flagged.
