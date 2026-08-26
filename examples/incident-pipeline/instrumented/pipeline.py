# instrumented/pipeline.py — the same pipeline, same data, same contradictory
# results, with one change: every stage derives its output through the
# provenance envelope, naming the exact code that produced it (the `basis`
# label), and each stored conclusion keeps its whole chain. The two runs still
# disagree — provenance does not fix a flipped sign — but the disagreement is
# now attributable in one read, instead of after months of re-derivation.
# Run: python3 instrumented/pipeline.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "primitives" / "python"))

from audit import audit_meta
from marked import derive, mark, meta_of

MEASUREMENTS = [12.1, 11.4, 13.0, 12.6, 11.9]  # instrument readings, dataset D42
BASELINE = 11.8


def calibrate_original(readings):
    return [x - BASELINE for x in readings]


def calibrate_inherited(readings):
    return [BASELINE - x for x in readings]  # operands reversed: the sign flip


def conclude(calibrated):
    mean = sum(calibrated) / len(calibrated)
    effect = "positive" if mean > 0 else "negative"
    return f"conclusion: effect: {effect} (mean {mean:+.2f})"


def analyse(calibrate, calibrate_label):
    """Run the pipeline, keeping each stage's envelope — that retained chain
    IS the stored lineage: the conditions that produced the conclusion."""
    raw = mark(MEASUREMENTS, source="real", confidence="high",
               basis="measurements.csv")
    processed = derive([raw], calibrate, basis=calibrate_label)
    conclusion = derive([processed], conclude, basis="analysis.mean_effect@v1")
    return conclusion, (conclusion, processed, raw)


def show(conclusion, chain):
    print("analysis — dataset D42")
    print(conclusion["value"])
    print("provenance chain:")
    conclusion_m, processed_m, raw_m = (meta_of(e) for e in chain)
    print(f"  {conclusion_m['basis']}")
    print(f"    <- {processed_m['basis']}")
    print(f"      <- {raw_m['basis']} [{raw_m['source']}/{raw_m['confidence']}]")


def main():
    for calibrate, label in [
        (calibrate_original, "preprocess.baseline_subtract@v1"),
        (calibrate_inherited, "preprocess.inherited@v2"),
    ]:
        conclusion, chain = analyse(calibrate, label)
        show(conclusion, chain)
        print("")

    # The incident's storage habit — a conclusion kept with no record of what
    # produced it — is itself flaggable: a derived value with no lineage is a
    # claim that cannot be audited.
    bare = mark("conclusion: effect: positive", source="derived")
    print("a conclusion stored bare (derived, no lineage):")
    for issue in audit_meta(meta_of(bare)):
        print(f"  {issue}")


if __name__ == "__main__":
    main()
