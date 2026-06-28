"""
services/source.py
Fetch/persist boundary — loads raw records from a data source.
Returns values WITH provenance, confidence, and a lineage field recording inputs.
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

    The returned dict records lineage so the result can be reproduced:
    - which source was used
    - how many records were loaded
    - the field names present in the records
    - the config version used for aggregation

    Args:
        config: dict with 'version' (str) and 'signal_threshold' (float)

    Returns:
        dict with keys:
            result          - float or None (None when no signal detected)
            signal_detected - bool
            mean            - float or None
            provenance      - str describing source and derivation
            confidence      - float 0–1; <1.0 when data is simulated
            data_status     - 'simulated' | 'live'
            lineage         - dict recording the inputs used to produce this result
            weights_version - str
    """
    records = list(_STUB_RECORDS)
    aggregated = aggregate_records(records, config)

    lineage = {
        "source": "stub/_STUB_RECORDS",
        "record_count": len(records),
        "field_names": list(records[0].keys()) if records else [],
        "config_version": config["version"],
    }

    return {
        "result": aggregated["result"],
        "signal_detected": aggregated["signal_detected"],
        "mean": aggregated["mean"],
        "provenance": f"stub source: {aggregated['provenance']}",
        "confidence": config["stub_confidence"],  # injected prior — trust level for stub data
        "data_status": "simulated",
        "lineage": lineage,
        "weights_version": aggregated["weights_version"],
    }
