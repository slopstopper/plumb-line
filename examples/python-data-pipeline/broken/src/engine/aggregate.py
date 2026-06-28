"""
engine/aggregate.py
Pure aggregation logic.
Layer: engine. Allowed imports: data only.
"""

from src.data.schema import NUMERIC_FIELDS

SIGNAL_THRESHOLD = 0.65


def aggregate_records(records, config):
    """
    Aggregate a list of records and determine whether a signal is present.

    Args:
        records: list of dicts, each with fields matching schema.FIELD_TYPES
        config:  dict with 'version' (str) and 'signal_threshold' (float)

    Returns:
        dict with keys:
            mean            - float or None
            signal_detected - bool
            result          - mean if signal detected, else None
            provenance      - str describing how the result was derived
            confidence      - float 0–1
            weights_version - str
    """
    if not records:
        return {
            "mean": None,
            "signal_detected": False,
            "result": None,
            "provenance": "no records provided",
            "confidence": 0.0,
            "weights_version": config["version"],
        }

    field = NUMERIC_FIELDS[0]
    values = [r[field] for r in records if field in r]

    if not values:
        return {
            "mean": None,
            "signal_detected": False,
            "result": None,
            "provenance": f"no values found for field '{field}'",
            "confidence": 0.0,
            "weights_version": config["version"],
        }

    threshold = SIGNAL_THRESHOLD
    mean = sum(values) / len(values)
    signal_detected = mean >= threshold

    return {
        "mean": mean,
        "signal_detected": signal_detected,
        "result": mean if signal_detected else None,
        "provenance": (
            f"mean({field}) over {len(values)} records = {mean:.4f}; "
            f"threshold={threshold}; "
            f"signal={'detected' if signal_detected else 'not detected'}"
        ),
        "confidence": 1.0 if signal_detected else 0.0,
        "weights_version": config["version"],
    }
