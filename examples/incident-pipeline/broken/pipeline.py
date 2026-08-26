# broken/pipeline.py — the incident, reconstructed. A small analysis pipeline:
# raw measurements are calibrated against a baseline, averaged, and stored as
# a one-line conclusion. The lab later inherits a "better" preprocessing
# script; somewhere inside it, the calibration is written the other way round,
# flipping every sign. Both conclusions below are computed correctly from
# their processing; they contradict each other; and the stored artifacts are
# indistinguishable — nothing records which code produced which number.
# Run: python3 broken/pipeline.py

MEASUREMENTS = [12.1, 11.4, 13.0, 12.6, 11.9]  # instrument readings, dataset D42
BASELINE = 11.8


def calibrate_original(readings):
    return [x - BASELINE for x in readings]


def calibrate_inherited(readings):
    # The inherited script's version of the "same" step. The operands are
    # reversed; every calibrated value comes out with its sign flipped.
    return [BASELINE - x for x in readings]


def conclude(calibrated):
    mean = sum(calibrated) / len(calibrated)
    effect = "positive" if mean > 0 else "negative"
    return f"conclusion: effect: {effect} (mean {mean:+.2f})"


def main():
    # The original analysis, as published.
    print("analysis — dataset D42")
    print(conclude(calibrate_original(MEASUREMENTS)))
    print("")
    # Months later: same data, same command, inherited script.
    print("analysis — dataset D42")
    print(conclude(calibrate_inherited(MEASUREMENTS)))


if __name__ == "__main__":
    main()
