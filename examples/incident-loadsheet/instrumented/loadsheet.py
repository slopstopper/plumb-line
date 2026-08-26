# instrumented/loadsheet.py — the same load sheet, same manifest, same total,
# with one change: each passenger weight is marked with how its category was
# known at the moment it is assigned. A category read from the booking record
# is real; a category guessed from an honorific is inferred, and the guess is
# labeled as such. The total, derived under the combination law, is then only
# as certain as its least certain input — and claiming otherwise is flagged.
# Run: python3 instrumented/loadsheet.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "primitives" / "python"))

from audit import audit_meta
from marked import derive, mark, meta_of

STANDARD_WEIGHT_KG = {"adult": 84, "child": 35}
TITLE_CATEGORY = {"Mr": "adult", "Mrs": "adult", "Ms": "adult",
                  "Miss": "child", "Master": "child"}

MANIFEST = [
    ("1A", "Mr",   "adult"),
    ("1B", "Mrs",  "adult"),
    ("2A", "Ms",   "adult"),
    ("2B", "Mr",   "adult"),
    ("3A", "Miss", None),
    ("3B", "Mr",   "adult"),
    ("4A", "Miss", None),
    ("4B", "Mrs",  "adult"),
    ("5A", "Miss", None),
    ("5B", "Mr",   "adult"),
]


def weigh(title, booked_category):
    """Assign the standard weight, marked with how the category was known.

    No passenger is weighed: every row is a standard-weight estimate, so no
    row can honestly claim high confidence. What varies is the input to the
    estimate — a category recorded in the booking (a fact, feeding an
    approved statistical prior: confidence medium) or a category guessed
    from an honorific (an estimate resting on a guess: inferred, low).
    """
    if booked_category is not None:
        return mark(STANDARD_WEIGHT_KG[booked_category],
                    source="real", confidence="medium")
    guessed = TITLE_CATEGORY[title]
    return mark(STANDARD_WEIGHT_KG[guessed],
                source="inferred", confidence="low")


def main():
    print("load sheet — flight PL123:")
    weights = []
    for seat, title, booked in MANIFEST:
        w = weigh(title, booked)
        weights.append(w)
        how = "booking" if booked is not None else "guessed from title"
        m = w["meta"]
        print(f"  {seat}  {title:<6} {w['value']} kg  [{m['source']}/{m['confidence']} — {how}]")

    total = derive(weights, lambda *kg: sum(kg), basis="loadsheet.total_mass@v1")
    print(f"total takeoff mass: {total['value']} kg")

    # The envelope answers what the printed total alone cannot: how much of
    # this number rests on a guess, and how sure anyone should be.
    meta = meta_of(total)
    inferred = sum(1 for step in meta["lineage"] if step["source"] == "inferred")
    print("")
    print("load sheet provenance:")
    print(f"  confidence: {meta['confidence']}")
    print(f"  weakest_source: {meta['weakest_source']}")
    print(f"  inferred inputs: {inferred}/{len(meta['lineage'])} (computed from lineage, not estimated)")

    # And the incident's exact move — issuing the sheet as fully confident —
    # is flagged by the runtime audit, because the lineage says otherwise.
    overclaimed = derive(weights, lambda *kg: sum(kg), confidence="high")
    print("")
    print('attempted over-claim (derive with confidence: "high"):')
    for issue in audit_meta(meta_of(overclaimed)):
        print(f"  {issue}")


if __name__ == "__main__":
    main()
