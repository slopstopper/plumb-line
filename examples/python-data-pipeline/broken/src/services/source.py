"""
services/source.py
Fetch/persist boundary — loads raw records from a data source.
Layer: services. Allowed imports: engine, data.
"""

from src.engine.aggregate import aggregate_records

# Stub dataset standing in for a real fetch (no external deps, no network calls).
_STUB_RECORDS = [
    {"id": "rec-001", "value": 0.72, "category": "alpha", "timestamp": "2024-01-01T00:00:00Z"},
    {"id": "rec-002", "value": 0.58, "category": "beta",  "timestamp": "2024-01-02T00:00:00Z"},
    {"id": "rec-003", "value": 0.81, "category": "alpha", "timestamp": "2024-01-03T00:00:00Z"},
]


def load_and_aggregate(config):
    """
    Load records from the data source and return an aggregated result.

    Args:
        config: dict with 'version' (str) and 'signal_threshold' (float)

    Returns:
        dict with keys:
            result          - float or None
            signal_detected - bool
            mean            - float or None
            provenance      - str
            confidence      - float 0–1
            data_status     - 'simulated' | 'live'
            weights_version - str
    """
    records = list(_STUB_RECORDS)
    aggregated = aggregate_records(records, config)

    return {
        "result": aggregated["result"],
        "signal_detected": aggregated["signal_detected"],
        "mean": aggregated["mean"],
        "provenance": f"stub source: {aggregated['provenance']}",
        "confidence": config["stub_confidence"],
        "data_status": "simulated",
        "weights_version": aggregated["weights_version"],
    }
