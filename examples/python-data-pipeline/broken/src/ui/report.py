"""
ui/report.py
Presentation layer — formats engine output as a human-readable report.
Imports engine only; never imports services or data directly.
Layer: ui (top). Allowed imports: engine only.
"""

from src.engine.aggregate import aggregate_records


def build_report(records, config):
    """
    Build a display-ready report string from engine output.
    Does not calculate — delegates entirely to the engine.

    Args:
        records: list of record dicts
        config:  dict with 'version' and 'signal_threshold'

    Returns:
        dict with keys:
            display_text    - str formatted for human display
            signal_detected - bool
            provenance      - str, passed through from engine for diagnostics
            confidence      - float, passed through from engine
    """
    result = aggregate_records(records, config)

    if result["signal_detected"]:
        summary = f"Signal detected. Mean value: {result['mean']:.4f}"
    else:
        summary = "No signal detected. Result: None"

    return {
        "display_text": (
            f"[Pipeline Report]\n"
            f"  {summary}\n"
            f"  Provenance: {result['provenance']}\n"
            f"  Confidence: {result['confidence']:.2f}\n"
            f"  Config version: {result['weights_version']}"
        ),
        "signal_detected": result["signal_detected"],
        "provenance": result["provenance"],
        "confidence": result["confidence"],
    }
